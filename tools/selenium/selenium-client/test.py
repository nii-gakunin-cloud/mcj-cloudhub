"""Module providing a function testing single-user notebook server."""
from __future__ import annotations
import datetime
from enum import Enum
import json
import logging
from multiprocessing import Pool, Manager
import os
import time
from urllib.parse import urlparse
import yaml

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class MCJUserTest():

    VIEW_TREE = 0
    VIEW_LAB = 1

    class ViewType(Enum):
        TREE = 0
        LAB = 1

    view_type = None

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(funcName)s:%(lineno)s [%(levelname)s]: %(message)s'))
    logger.addHandler(handler)

    def __init__(self, moodle_url: str, headless: bool = False,
                 browser: str = "chrome", auto_exit: bool = True,
                 timeout: int = 60) -> None:

        if browser == "firefox":
            options = webdriver.FirefoxOptions()
            if headless:
                options.add_argument('--headless')
            # options.add_argument("log-level=3")

            try:
                self.driver = webdriver.Remote(
                    command_executor='http://selenium-executer:4444/wd/hub',
                    options=options
                )
            except Exception as e:
                print(e)
                raise e
        elif browser == "chrome":
            options = webdriver.ChromeOptions()
            if headless:
                options.add_argument('--headless')

            # options.add_argument("log-level=3")
            self.driver = webdriver.Remote(
                command_executor='http://selenium-executer:4444/wd/hub',
                options=options
            )

        self.auto_exit = auto_exit
        self.current_window = 0
        self.wait = WebDriverWait(self.driver, timeout)

        self.moodle_url = moodle_url

    def __del__(self):
        self.quit()

    def _get_tab_list(self):
        time.sleep(5)
        self.wait.until(EC.visibility_of_element_located(
            (By.ID, "jp-main-dock-panel")))
        panel = self.driver.find_element(By.ID, "jp-main-dock-panel")
        return panel.find_element(By.XPATH, './/*[@role="tablist"]')

    def _get_active_tab(self):
        tab_list = self._get_tab_list()
        active_tab = tab_list.find_element(
            By.XPATH, './/li[@role="tab" and @aria-selected="true"]')
        tab = self.driver.find_element(
            By.ID, active_tab.get_attribute('data-id'))
        return tab

    def _get_active_file_name(self):
        tab_list = self._get_tab_list()
        active_tab = tab_list.find_element(
            By.XPATH, './/li[@role="tab" and @aria-selected="true"]')

        file_name = active_tab.find_element(
            By.XPATH, './/div[@class="lm-TabBar-tabLabel p-TabBar-tabLabel"]'
        ).text
        return file_name

    def _element_text_to_be_changed(self, locator, text):
        def _predicate(driver):
            return driver.find_elements(*locator) != text
        return _predicate

    def quit(self):
        if hasattr(self, 'driver'):
            self.driver.quit()
            self.logger.debug('Web driver quitted')

    def login_moodle(self, user_name, password):

        self.driver.get(self.moodle_url + "/login/index.php")

        username_input = self.driver.find_element(By.ID, 'username')
        username_input.send_keys(user_name)
        elem_password = self.driver.find_element(By.ID, 'password')

        # moodle=4.4 では入力したパスワードがすぐにクリアされてしまい、ログインできない
        # moodle=4.2.7では現象が起きない
        elem_password.click()
        elem_password.send_keys(password)

        login_button = self.driver.find_element(By.ID, 'loginbtn')
        login_button.click()
        error_message = "timeout"

        time.sleep(1)
        try:
            # # URLがマッチするかログインエラーメッセージが出るまで待機
            # WebDriverWait(self.driver, 60).until(
            #     lambda driver: driver.find_element(By.ID, 'loginerrormessage') or EC.url_matches("/my/")(driver)
            # )

            for _ in range(60):

                try:
                    # エラーメッセージをチェック
                    error_message_element = self.driver.find_element(By.ID, 'loginerrormessage')
                    error_message = error_message_element.text
                    raise TimeoutException()

                except NoSuchElementException:
                    # エラーメッセージが見つからない場合は無視
                    pass

                try:
                    # URLが /my/ にマッチするかどうかをチェック
                    WebDriverWait(self.driver, 5).until(EC.url_matches("/my/"))
                    # URLがマッチすればログイン成功
                    return
                except TimeoutException:
                    # URLがまだマッチしていない場合は無視
                    pass

        except TimeoutException:
            # 例外処理（ログインに失敗した場合）
            self.logger.error("user [%s]: Moodle login failed: '%s'", user_name, error_message)
            raise e("user [%s]: Moodle login failed: '%s'", user_name, error_message)

        if self.auto_exit:
            self.driver.quit()

    def get_tool_id(self, tool_name: str, course_name: str):
        self.driver.get(f"{self.moodle_url}/my/courses.php")

        main_elem = self.driver.find_element(By.ID, 'region-main-box')
        course_list = main_elem.find_element(
            By.XPATH, '//div[@data-region="courses-view"]')

        # 表示待ち
        time.sleep(5)

        for course in course_list.find_elements(
                By.XPATH, './/div[@data-region="course-content"]'):

            if course.find_element(By.XPATH, './/span[@class="sr-only"]').text == course_name:
                course_id = course.get_attribute('data-course-id')
                self.driver.get(
                    f"{self.moodle_url}/course/view.php?id={course_id}")
                break
        else:
            raise ValueError('Course not found')

        for activity_elem in self.driver.find_elements(By.CLASS_NAME, 'activity-item'):
            if activity_elem.get_attribute('data-activityname') == tool_name:
                tid = activity_elem.find_element(
                    By.XPATH, "..").get_attribute('data-id')
                break

        return tid

    def select_lti_url(self, tool_id: int):

        current_window_count = len(self.driver.window_handles)
        self.driver.get(f"{self.moodle_url}/mod/lti/view.php?id={tool_id}")
        self.wait.until(EC.number_of_windows_to_be(
            current_window_count + 1))
        self.switch_window()
        self.wait.until(EC.url_contains(
            'user'))

        return self.driver.current_url

    def switch_window(self, step=1):

        self.driver.switch_to.window(
            self.driver.window_handles[self.current_window + step])

        self.current_window += step

        return self.driver.current_url

    def _wait_tab_added(self, current_tab_count):

        def check_tab_count(locator, target_count):
            def _predicate(driver):
                return len(driver.find_elements(*locator)) >= target_count
            return _predicate

        # タブ数が増えるのを待つ
        wait = WebDriverWait(self._get_tab_list(), 10)
        wait.until(check_tab_count((By.TAG_NAME, "li"), current_tab_count + 1),
                   "Not Succeeded to open launcher")

    def _open_new_notebook_tree(self, kernel=None):

        # 表示待ち
        time.sleep(10)

        kernel = kernel if kernel is not None else "python3"
        # classic notebook view
        self.wait.until(EC.visibility_of_element_located(
            (By.ID, "new-dropdown-button")))
        elem = self.driver.find_element(By.ID, 'new-dropdown-button')
        elem.click()

        current_window_count = len(self.driver.window_handles)

        elem = self.wait.until(EC.element_to_be_clickable(
            (By.ID, f'kernel-{kernel}')))
        elem.click()
        self.wait.until(EC.number_of_windows_to_be(current_window_count + 1))
        self.switch_window()

        time.sleep(5)
        new_file_name = self.wait.until(
            EC.presence_of_element_located((By.ID, "notebook_name"))).text
        return new_file_name + '.ipynb'

    def _open_new_notebook_lab(self, kernel=None):

        time.sleep(10)

        # カーネル選択モーダルが開いている場合は閉じる
        # ダイアログは閉じたら次の物が開く。カーネル未選択のNotebookが開いていると、１つ閉じては開く
        # 前回実行時にNotebookを開いて何もしないと、次回Jupyterを開いたときにカーネル未選択状態となっているため、繰り返すごとに開くモーダル数が＋１される。
        max_retry = 100
        for _ in range(max_retry):
            dialogs = self.driver.find_elements(By.CLASS_NAME, 'jp-Dialog')
            if len(dialogs) == 0:
                break

            self.logger.debug('%s dialog(s) detected', len(dialogs))

            for dialog in dialogs:
                dialog.find_element(
                    By.XPATH, './/button[contains(@class, "jp-mod-reject")]').click()
                time.sleep(1)

        self.wait.until(EC.visibility_of_element_located(
            (By.ID, "jp-main-dock-panel")))
        panel = self.driver.find_element(By.ID, "jp-main-dock-panel")

        # 現在のタブ数
        tab_count = len(self._get_tab_list().find_elements(By.TAG_NAME, "li"))
        try:
            wait = WebDriverWait(panel, 30)
            wait.until(EC.element_to_be_clickable(
                (By.XPATH, './/*[@title="New Launcher"]')))
            launcher_button = panel.find_element(
                By.XPATH, './/*[@title="New Launcher"]')
            launcher_button.click()
            self._wait_tab_added(tab_count)
        except Exception as e:
            self.logger.error(e)
            raise e

        time.sleep(5)
        tab = self._get_active_tab()
        kernels = tab.find_elements(
            By.XPATH, './/div[@class="jp-LauncherCard" and @data-category="Notebook"]')
        kernel_idx = 0

        if kernel is not None:
            for i, k in enumerate(kernels):
                if kernel == k.get_attribute('title'):
                    kernel_idx = i
        try:
            # 単純にクリックすると他の要素との関係でクリックに失敗できない時がある
            self.driver.execute_script(
                "arguments[0].click();", kernels[kernel_idx])
        except Exception as e:
            self.logger.error(e)
            raise e

        # launcherタブがNotebookタブに変化するのを待つ
        time.sleep(5)
        current_tab = self._get_active_tab()
        WebDriverWait(current_tab, 60).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '.jp-Notebook-cell')),
            'Timeout to get locate cells'
        )
        return self._get_active_file_name()

    def open_new_notebook(self, view_type, kernel=None):

        if view_type == self.ViewType.TREE.value:
            return self._open_new_notebook_tree(kernel)
        else:
            return self._open_new_notebook_lab(kernel)

    def _edit_notebook_tree(self, code_execute=None, delete_after=False):

        notebook_name = self.wait.until(
            EC.presence_of_element_located((By.ID, "notebook_name"))).text

        notebook_container = self.wait.until(
            EC.presence_of_element_located((By.ID, "notebook-container")))
        cell = WebDriverWait(notebook_container, 60).until(
            EC.presence_of_element_located(
                (By.XPATH, './/div[contains(@class, "code_cell") and contains(@class, "selected")]')),
            'Timeout to get locate active cell'
        )
        cell.click()
        cell.find_element(By.TAG_NAME, 'textarea').send_keys(code_execute)

        input_prompt = cell.find_element(
            By.XPATH, ".//div[@class='prompt input_prompt']")
        input_prompt_before = input_prompt.text

        self.logger.debug('exec start')
        wait = WebDriverWait(cell, 120)
        wait.until(
            self._element_text_to_be_changed(
                (By.XPATH, ".//div[@class='prompt input_prompt']"),
                input_prompt_before),
            'Execute cell timeout'
        )
        self.logger.debug('exec finished')
        self.driver.find_element(
            By.XPATH, "//button[@aria-label='Run']").click()

        output_wrapper = WebDriverWait(cell, 300).until(
            EC.visibility_of_element_located(
                (By.CLASS_NAME, "output_wrapper")),
            'Timeout waiting output to be visible'
        )
        output_txt = WebDriverWait(output_wrapper, 300).until(
            EC.visibility_of_element_located((By.TAG_NAME, "pre")),
            'Timeout waiting output to be visible'
        ).text

        if delete_after:
            # Notebookタブを閉じてからタブ遷移を行い、ファイルの削除を行う
            # 削除対象のNotebookが開いたままだと、ダイアログが出て処理が止まるため。
            self.driver.close()
            self.switch_window(step=-1)
            # ファイル一覧が更新されていない場合があるので更新ボタンを押しておく
            self.wait.until(EC.visibility_of_element_located(
                (By.ID, "refresh_notebook_list"))).click()
            row = WebDriverWait(
                self.driver.find_element(By.ID, 'notebook_list'), 30
            ).until(EC.visibility_of_element_located(
                (By.XPATH, f".//span[@class='item_name' and text()='{notebook_name}.ipynb']")),
                'Failed to found target row'
            )

            row_parent = row.find_element(By.XPATH, "../..")
            check = row_parent.find_element(
                By.XPATH, ".//input[@type='checkbox']")
            check.click()

            self.driver.find_element(
                By.XPATH, "//button[contains(@class,'delete-button')]").click()
            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[@class='btn btn-default btn-sm btn-danger' and @data-dismiss='modal']"))).click()

        return output_txt

    def _edit_notebook_lab(self, code_execute=None, delete_after=False):

        panel = self._get_active_tab()
        wait = WebDriverWait(panel, 60)
        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '.jp-Notebook-cell')),
            'Timeout to get locate cells'
        )

        cell = panel.find_element(By.CLASS_NAME, 'jp-mod-active')
        wait.until(
            EC.element_to_be_clickable((By.CLASS_NAME, 'jp-InputArea-editor')),
            'Timeout to cell to be clickable'
        )
        cells = panel.find_elements(By.CLASS_NAME, 'jp-InputArea-editor')
        self.driver.execute_script("arguments[0].click();", cells[0])

        textarea = WebDriverWait(cells[0], 60).until(
            EC.presence_of_element_located((By.XPATH, './/textarea')),
            'Timeout to get cell to be intaractable'
        )
        textarea.send_keys(code_execute)

        input_prompt = cell.find_element(
            By.XPATH, ".//div[@class='lm-Widget p-Widget jp-InputPrompt jp-InputArea-prompt']")
        input_prompt_before = input_prompt.text

        # execute
        panel.find_element(
            By.XPATH, ".//*[@data-command='runmenu:run']").click()

        self.logger.debug('exec start')
        wait = WebDriverWait(cell, 120)
        wait.until(
            self._element_text_to_be_changed(
                (By.XPATH, ".//div[@class='lm-Widget p-Widget jp-InputPrompt jp-InputArea-prompt']"),
                input_prompt_before),
            'Execute cell timeout'
        )
        self.logger.debug('exec finished')

        # kernelの実行が完了してすぐにはoutputの編集が終わっていない場合があるのでこちらも待機する
        output = cell.find_element(By.CLASS_NAME, 'jp-Cell-outputWrapper')
        wait = WebDriverWait(output, 120)
        output_txt = wait.until(
            EC.visibility_of_element_located((By.TAG_NAME, "pre"))
        ).text
        # output_txt = output.find_element(By.TAG_NAME, 'pre').text

        if delete_after:

            file_name = self._get_active_file_name()
            files = self.driver.find_element(
                By.CLASS_NAME, 'jp-DirListing-content'
                ).find_elements(By.TAG_NAME, "li")

            for file in files:
                try:
                    target = file.find_element(
                        By.XPATH, f".//span[text()='{file_name}']")
                    target.click()
                    actions = ActionChains(self.driver)
                    actions.context_click(target).perform()
                    time.sleep(1)
                    self.wait.until(EC.element_to_be_clickable(
                        (By.XPATH, "//li[@role='menuitem' and @data-command='filebrowser:delete']"))).click()
                    time.sleep(3)
                    self.wait.until(EC.element_to_be_clickable(
                        (By.XPATH, "//button[@class='jp-Dialog-button jp-mod-accept jp-mod-warn jp-mod-styled']"))).click()
                    time.sleep(3)
                    break
                except NoSuchElementException:
                    continue
                except Exception as e:
                    self.logger.error(type(e))
                    self.logger.error(e)
                    raise e

        return output_txt

    def edit_notebook(self, view_type, code_execute=None, delete_after=False):

        if view_type == self.ViewType.TREE.value:
            return self._edit_notebook_tree(code_execute, delete_after)
        else:
            return self._edit_notebook_lab(code_execute, delete_after)

    def log_out(self):
        o = urlparse(self.driver.current_url)
        self.driver.get(f'{o.scheme}://{o.netloc}/hub/logout')
        try:
            # セル実行後にファイルを保存しない場合、保存要否を問うアラートが出てログアウト処理が完了できないため、アラートを閉じる
            wait = WebDriverWait(self.driver, 5)
            wait.until(EC.alert_is_present())
            alert = self.driver.switch_to.alert
            alert.accept()
        except TimeoutException:
            pass


def main(user_info: dict,
         moodle_url: str,
         tool_id: int = -1,
         tool_name: str = None,
         course_name: str = None,
         browser: str = "chrome",
         headless: bool = True,
         timeout: int = 60,
         exec_src: str = None,
         logout: bool = True,
         result_output_file: str = None,
         file_lock=None,):

    def _output_result(lock, output: str, info: dict):

        if lock is not None:
            lock.acquire()

        try:
            if os.path.isfile(output):
                with open(output, mode='r', encoding='utf-8') as f:
                    d = json.load(f)
            else:
                d = dict()

            for k in info:
                d[k] = info[k]

            updated_json = json.dumps(d, indent=4)
            # JSONファイルに更新データを書き込む
            with open(output, 'w', encoding='utf-8') as f:
                f.write(updated_json)

        except Exception as e:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(f'Failed to write result file({output}): {str(e)}')
            raise e

        finally:
            if lock is not None:
                lock.release()

    if tool_id < 0 and tool_name is None:
        raise ValueError('course_name and tool_name is required if tool_id is not specified.')

    ut = MCJUserTest(moodle_url, headless, browser=browser,
                     auto_exit=False, timeout=timeout)

    result = dict(status='ng', started=datetime.datetime.now().isoformat(), detail=[])
    try:

        # moodleにログイン
        ut.login_moodle(
            user_name=user_info['username'], password=user_info['password'])

        ut.logger.info('user [%s]: login to moodle.',
                       user_info["username"])
        # moodleのコースを選択して、外部ツールのURLを踏んでJupyterhubにログイン
        # tool_idを直接指定する or コース名とツール名を指定し、ブラウザ操作によりアクセスしてtoolリンクを踏む
        if tool_id < 0:
            tid = ut.get_tool_id(tool_name, course_name)
        else:
            tid = tool_id

        current_url = ut.select_lti_url(tid)

        # lab/tree 判別
        o = urlparse(current_url)
        if o.path.find('tree'):
            view_type = ut.ViewType.TREE
        elif o.path.find('lab'):
            view_type = ut.ViewType.LAB
        else:
            raise Exception("Spawn failed")

        ut.logger.info('user [%s]: jupyter server launched. View type: %s',
                        user_info["username"],
                        view_type.name)

        result['detail'].append({'spawn': 'ok'})

        if exec_src is not None:
            # # jupyter上でホームに移動（labでは不要？）
            # ut.go_home_jh()
            # テスト用に新規ノートブックを開く
            # ut.open_new_notebook(kernel='LC_wrapper')
            # ut.open_new_notebook(kernel='Python 3 (ipykernel)')
            file_name = ut.open_new_notebook(view_type.value)

            ut.logger.info('user [%s]: new notebook [%s] opened',
                            user_info["username"],
                            file_name)

            exec_output = ut.edit_notebook(view_type.value,
                                           code_execute=exec_src,
                                           delete_after=True)
            result['detail'].append({'exec_output': exec_output})

            ut.logger.debug('user [%s]: output: "%s"',
                            user_info["username"],
                            exec_output)

        if logout:
            ut.log_out()

        result['status'] = 'ok'

    except Exception as e:
        ut.logger.error(type(e))
        ut.logger.error(e)
        result['error'] = str(e)
        raise e

    finally:
        if result_output_file is not None:
            result['finished'] = datetime.datetime.now().isoformat()
            _output_result(file_lock, result_output_file, {user_info['username']: result})



if __name__ == "__main__":

    # 前提条件
    # moodle==4.2.7
    # Python3.10.11

    # Tips
    # まずはファイル指定せず、1ユーザのみで起動できることを確認する。
    # 1ユーザで起動確認ができたら、ファイル指定して多人数起動を試験する。（headless=Trueとすることを推奨）

    import argparse
    import csv

    parser = argparse.ArgumentParser(
        prog='test',
        description='read csv',)

    parser.add_argument('filename')
    args = parser.parse_args()

    users = list()
    file_ext = os.path.splitext(args.filename)[1]
    with open(args.filename, encoding='utf8') as f:
        if '.csv' == file_ext:
            csv_data = list(csv.DictReader(f))
            for d in csv_data:
                users.append(
                    dict(username=d['username'], password=d['password'])
                )
        elif file_ext in ('.yaml', '.yml'):
            users = yaml.safe_load(f)

    HEADLESS = False
    m = Manager()
    result_file_lock = m.Lock()

    LMS_URL = os.environ['LMS_URL']

    # 1. 外部ツールIDを指定する場合（外部ツールのリンクのクエリパラメータで確認）（推奨）
    TOOL_ID = int(os.environ['LMS_TOOL_ID'])
    COURSE_NAME = None
    TOOL_NAME = None
    CODE_EXEC = os.getenv('CODE_EXEC')

    # 2. コース名・ツール名を指定し、seleniumに検索させる場合
    # TOOL_ID = -1
    # COURSE_NAME = 'mcj'
    # TOOL_NAME = 'jupyterhub'

    OUTPUT_FILE = None
    if os.getenv('RESULT_OUTPUT'):
        date = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        OUTPUT_FILE = os.path.join(os.path.dirname(__file__), 'result', f'result_{date}.json')
        if os.path.isfile(OUTPUT_FILE):
            os.remove(OUTPUT_FILE)

    p = Pool(len(users))
    for user in users:
        # timeoutは、コンテナのspawn時間より長くする 同時起動数が多いと各ユーザのspawn時間も延びる？
        p.apply_async(main,
                      args=(user, LMS_URL),
                      kwds=dict(tool_id=TOOL_ID, tool_name=TOOL_NAME, course_name=COURSE_NAME,
                                browser="firefox", headless=HEADLESS, file_lock=result_file_lock,
                                result_output_file=OUTPUT_FILE, logout=False, exec_src=CODE_EXEC))

    print('Start each subprocesses')
    p.close()
    p.join()
    print('All subprocesses done.')

    # main(users[0], headless, 60)

