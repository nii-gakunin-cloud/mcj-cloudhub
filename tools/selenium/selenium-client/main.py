"""Module providing a function testing single-user notebook server."""
from __future__ import annotations
from abc import abstractmethod
import argparse
import csv
import datetime
import json
import logging
from multiprocessing import Pool, Manager
import os
import time
from typing import Union
from urllib.parse import urlparse
import yaml

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (TimeoutException,
                                        NoSuchElementException,
                                        StaleElementReferenceException)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class MCJUserTestBase():

    class MCJUserTestException(Exception):
        def __init__(self, arg=''):
            self.arg = arg

    def __init__(self, user_name, executer=None, driver=None, logger=None,
                 headless=True, browser='chrome', common_timeout=30):
        """constructor for test class
        """

        if executer is None and driver is None:
            raise self.MCJUserTestException("executer or driver is required")

        self.user_name = user_name
        self.logger = logger if logger is not None else self.get_logger()
        self.driver = driver if driver is not None else self.get_driver(
            executer, headless, browser)
        self.wait = WebDriverWait(self.driver, common_timeout)
        self.current_window = 0

    class ContextFilter(logging.Filter):
        """
        This is a filter which injects contextual information into the log.
        """
        def __init__(self, name='', user_name=''):
            super().__init__(name)
            self.user_name = user_name

        def filter(self, record):
            record.user = self.user_name
            return True

    def get_logger(self):
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s %(funcName)s:%(lineno)s [%(levelname)s]: [%(user)s] %(message)s'))
        logger.addHandler(handler)
        logger.addFilter(self.ContextFilter(user_name=self.user_name))
        return logger

    def get_driver(self, executer, headless: bool = True, browser='chrome'):
        if browser == "firefox":
            options = webdriver.FirefoxOptions()
        elif browser == "chrome":
            options = webdriver.ChromeOptions()
        else:
            options = webdriver.ChromeOptions()

        if headless:
            options.add_argument('--headless')

        return webdriver.Remote(
            command_executor=executer,
            options=options
        )

    def switch_window(self, step=1):
        self.driver.switch_to.window(
            self.driver.window_handles[self.current_window + step])
        self.current_window += step
        return self.driver.current_url


class JupyterViewTestBase(MCJUserTestBase):

    def __init__(self, user_name, executer=None, driver=None, logger=None,
                 headless=True, browser='chrome', common_timeout=10):
        super().__init__(user_name, executer, driver, logger, headless, browser, common_timeout=common_timeout)

    @abstractmethod
    def open_notebook(self):
        pass

    @abstractmethod
    def edit_notebook(self):
        pass

    @abstractmethod
    def delete_notebook(self):
        pass


class JupyterViewTestTree(JupyterViewTestBase):

    class ElementCellExecuted(object):
        """An expectation for checking that an element has a particular css class.

        returns the cell execution status

        examples:
            result = wait.until(ElementCellExecuted(cell))
        """
        cell_status_success = 'cell-status-success'
        cell_status_failed = 'cell-status-error'

        def __init__(self, cell_element):
            self.element = cell_element

        def __call__(self, driver):
            if self.cell_status_success in self.element.get_attribute("class"):
                return self.cell_status_success
            elif self.cell_status_failed in self.element.get_attribute("class"):
                return self.cell_status_failed
            else:
                return False

    def _open_new_notebook(self, kernel=None):

        # 表示待ち
        time.sleep(10)
        kernel = kernel if kernel is not None else "python3"
        # classic notebook view
        self.wait.until(EC.visibility_of_element_located(
            (By.ID, "new-dropdown-button")))
        self.driver.find_element(By.ID, 'new-dropdown-button').click()
        window_count = len(self.driver.window_handles)
        self.wait.until(EC.element_to_be_clickable(
            (By.ID, f'kernel-{kernel}'))).click()
        self.wait.until(EC.number_of_windows_to_be(window_count + 1))
        self.switch_window(window_count-self.current_window)
        wait = WebDriverWait(self.driver, 60)
        new_file_name = wait.until(
            EC.presence_of_element_located((By.ID, "notebook_name"))).text
        return new_file_name + '.ipynb'

    def _edit_notebook(self, code_execute=None):

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

        # TODO 入力完了まで待機
        time.sleep(5)

        self.logger.info('exec pre')
        wait = WebDriverWait(cell, 120)
        time.sleep(1)
        self.driver.find_element(
            By.XPATH, "//button[@aria-label='Run']").click()

        self.logger.info('exec started')
        wait = WebDriverWait(cell, 600)
        # Wait cell status to be changed
        result = wait.until(self.ElementCellExecuted(cell))

        # Wait cell output area to be shown
        output_wrapper = WebDriverWait(cell, 30).until(
            EC.visibility_of_element_located(
                (By.CLASS_NAME, "output_wrapper")),
            'Timeout waiting output to be located'
        )

        # Wait getting cell output
        output_txt = WebDriverWait(output_wrapper, 30).until(
            EC.visibility_of_element_located((By.TAG_NAME, "pre")),
            'Timeout waiting output to be visible'
        ).text

        self.logger.info(f'result: {result} output: {output_txt}')
        wait = WebDriverWait(self.driver, 10)
        save_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[title="Save and Checkpoint"]')))
        save_button.click()
        self.logger.info('notebook saved')
        return output_txt, notebook_name

    def _delete_notebook(self, notebook_name: str):

        # Notebookタブを閉じてからタブ遷移を行い、ファイルの削除を行う
        # 削除対象のNotebookが開いたままだと、ダイアログが出て処理が止まるため。
        self.driver.close()
        time.sleep(1)
        self.switch_window(step=-1)
        time.sleep(1)
        # ファイル一覧が更新されていない場合があるので更新ボタンを押しておく
        self.wait.until(EC.visibility_of_element_located(
            (By.ID, "refresh_notebook_list")), "Timeout to refresh notebook list").click()
        checkbox_xpath = f"//div[contains(@class, 'list_item') and .//span[@class='item_name' and text()='{notebook_name}.ipynb']]//input[@type='checkbox']"
        wait = WebDriverWait(self.driver, 60)
        wait.until(EC.presence_of_element_located((By.XPATH, checkbox_xpath)), "Timeout to find checkbox for select notebook")
        for _ in range(10):
            try:
                self.wait.until(EC.element_to_be_clickable((
                    By.XPATH, checkbox_xpath))).click()
                break
            except StaleElementReferenceException:
                time.sleep(1)
        self.driver.find_element(
            By.XPATH, "//button[contains(@class,'delete-button')]").click()
        self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[@class='btn btn-default btn-sm btn-danger' and @data-dismiss='modal']"))).click()

    def open_new_notebook(self, kernel=None):
        return self._open_new_notebook(kernel)

    def edit_notebook(self, code_execute=None):
        return self._edit_notebook(code_execute)

    def delete_notebook(self, notebook_name):
        return self._delete_notebook(notebook_name)


class JupyterViewTestLab(JupyterViewTestBase):

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

    def _wait_tab_added(self, current_tab_count):

        def check_tab_count(locator, target_count):
            def _predicate(driver):
                return len(driver.find_elements(*locator)) >= target_count
            return _predicate

        # タブ数が増えるのを待つ
        wait = WebDriverWait(self._get_tab_list(), 10)
        wait.until(check_tab_count((By.TAG_NAME, "li"), current_tab_count + 1),
                   "Not Succeeded to open launcher")

    def _open_new_notebook(self, kernel=None):

        # カーネル選択モーダルが開いている場合は閉じる
        # ダイアログは閉じたら次の物が開く。カーネル未選択のNotebookが開いていると、１つ閉じては開く
        # 前回実行時にNotebookを開いて何もしないと、次回Jupyterを開いたときにカーネル未選択状態となっているため、
        # 繰り返すごとに開くモーダル数が＋１される。
        max_retry = 100
        for _ in range(max_retry):
            dialogs = self.driver.find_elements(By.CLASS_NAME, 'jp-Dialog')
            if len(dialogs) == 0:
                break

            self.logger.info('%s dialog(s) detected', len(dialogs))

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

    def _delete_notebook(self, notebook_name: str):

        files = self.driver.find_element(
            By.CLASS_NAME, 'jp-DirListing-content'
            ).find_elements(By.TAG_NAME, "li")

        for file in files:
            try:
                target = file.find_element(
                    By.XPATH, f".//span[text()='{notebook_name}']")
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

    def _edit_notebook(self, code_execute=None):

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

        self.logger.info('exec start')
        wait = WebDriverWait(cell, 120)
        wait.until(
            self._element_text_to_be_changed(
                (By.XPATH, ".//div[@class='lm-Widget p-Widget jp-InputPrompt jp-InputArea-prompt']"),
                input_prompt_before),
            'Execute cell timeout'
        )
        self.logger.info('exec finished')

        # kernelの実行が完了してすぐにはoutputの編集が終わっていない場合があるのでこちらも待機する
        output = cell.find_element(By.CLASS_NAME, 'jp-Cell-outputWrapper')
        wait = WebDriverWait(output, 120)
        output_txt = wait.until(
            EC.visibility_of_element_located((By.TAG_NAME, "pre"))
        ).text

        file_name = self._get_active_file_name()
        return output_txt, file_name

    def open_new_notebook(self, kernel=None):
        return self._open_new_notebook(kernel)

    def edit_notebook(self, code_execute=None):
        return self._edit_notebook(code_execute)

    def delete_notebook(self, notebook_name):
        return self._delete_notebook(notebook_name)


class MCJUserSpawnTest(MCJUserTestBase):

    view_type = None

    def __init__(self, moodle_url: str, executer: str, headless: bool = False,
                 browser: str = "chrome", auto_exit: bool = True,
                 common_timeout: int = 10, user_name="", user_password="",
                 logger=None, driver=None) -> None:

        super().__init__(user_name, executer, driver, logger,
                         headless, browser, common_timeout=common_timeout)
        self.auto_exit = auto_exit
        self.moodle_url = moodle_url
        self.user_password = user_password

    def quit(self):
        if hasattr(self, 'driver'):
            self.driver.quit()
            self.logger.info('Web driver quitted')

    def __del__(self):
        self.quit()

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

    # Moodle
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
        script = f"window.open('{self.moodle_url}/mod/lti/launch.php?id={tool_id}', 'lti-{tool_id}');"
        self.driver.execute_script(script)
        WebDriverWait(self.driver, 600).until(EC.number_of_windows_to_be(
            current_window_count + 1))
        self.switch_window()
        WebDriverWait(self.driver, 600).until(EC.url_contains(
            'user'))
        return self.driver.current_url

    def login_moodle(self):

        self.driver.get(self.moodle_url + "/login/index.php")
        time.sleep(5)
        self.driver.find_element(By.ID, 'username').send_keys(self.user_name)
        self.driver.find_element(By.ID, 'password').click()
        self.driver.find_element(By.ID, 'password').send_keys(self.user_password)
        self.driver.find_element(By.ID, 'loginbtn').click()
        error_message = "timeout"
        time.sleep(1)
        try:

            for _ in range(60):

                try:
                    error_message = self.driver.find_element(
                        By.ID, 'loginerrormessage').text
                    raise TimeoutException()

                except NoSuchElementException:
                    pass

                try:
                    WebDriverWait(self.driver, 5).until(EC.url_matches("/my/"))
                    return
                except TimeoutException:
                    pass

        except TimeoutException as e:
            # 例外処理（ログインに失敗した場合）
            self.logger.error("Moodle login failed: '%s'", error_message)
            raise TimeoutException(msg=f"Moodle login failed: '{error_message}'") from e

        if self.auto_exit:
            self.driver.quit()


def main(user_info: dict,
         moodle_url: str,
         executer: str,
         tool_id: Union[int, None] = None,
         tool_name: str = None,
         course_name: str = None,
         browser: str = "chrome",
         headless: bool = True,
         common_timeout: int = 10,
         exec_src: str = None,
         logout: bool = True,
         result_output_file: str = None,
         file_lock=None,
         screenshot_dir: str = '/app/result/images'):

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

            updated_json = json.dumps(d, indent=4, ensure_ascii=False)
            with open(output, 'w', encoding='utf-8') as f:
                f.write(updated_json)

        except Exception as e:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(f'Failed to write result file({output}): {str(e)}')
            raise e

        finally:
            if lock is not None:
                lock.release()

    st = MCJUserSpawnTest(moodle_url, executer, headless, browser=browser,
                          auto_exit=False, common_timeout=common_timeout,
                          user_name=user_info['username'],
                          user_password=user_info['password'])
    logger = st.logger
    result = dict(status='ng',
                  started=datetime.datetime.now().isoformat(),
                  detail=[])
    try:
        # moodleにログイン
        st.login_moodle()
        result['detail'].append({'login_moodle': 'ok'})
        logger.info('login to moodle')
        # moodleのコースを選択して、外部ツールのURLを踏んでJupyterhubにログイン
        # tool_idを直接指定する or コース名とツール名を指定し、ブラウザ操作によりアクセスしてtoolリンクを踏む
        if tool_id is None:
            tid = st.get_tool_id(tool_name, course_name)
        else:
            tid = int(tool_id)

        try:
            _ = st.select_lti_url(tid)
        except TimeoutException as e:
            result['error'] = f'Timeout to open Jupyter home: tool_id: {tid}'
            raise e

        WebDriverWait(st.driver, 120).until(EC.url_matches(
            r'.*(tree|lab).*'),
            f'URL is not expected one: {st.driver.current_url}')

        # lab/tree 判別
        o = urlparse(st.driver.current_url)

        view_tree, view_lab = 'tree', 'lab'
        jt = None
        if o.path.find('tree') > 0:
            view_type = view_tree
            jt = JupyterViewTestTree(user_name=user_info['username'],
                                     logger=logger, driver=st.driver)
        elif o.path.find('lab') > 0:
            view_type = view_lab
            jt = JupyterViewTestLab(user_name=user_info['username'],
                                    logger=logger, driver=st.driver)
        else:
            raise Exception(f"Spawn failed or url is not expected one: {o}")

        logger.info('jupyter server launched. View type: %s',
                    view_type)
        result['detail'].append({'spawn': 'ok'})

        if exec_src is not None:
            file_name = jt.open_new_notebook()

            logger.info('new notebook [%s] opened',
                        file_name)

            exec_output, notebook_name = jt.edit_notebook(
                code_execute=exec_src)
            result['detail'].append({'exec_output': exec_output})

            logger.info('output: "%s"', exec_output)

            jt.delete_notebook(notebook_name)

        result['status'] = 'ok'

    except StaleElementReferenceException as e:
        logger.error(e)
        result['exception_message'] = f'Element may be clicked when not ready {str(e)}'
        st.driver.save_screenshot(os.path.join(screenshot_dir,
                                               f'{st.user_name}_error.png'))
        raise e

    except TimeoutException as e:
        logger.error(e)
        result['exception_message'] = f'Timeout occured {e}'
        raise e

    except Exception as e:
        logger.error(type(e))
        logger.error(e)
        result['exception_message'] = str(e)
        raise e

    finally:
        if result_output_file is not None:
            result['finished'] = datetime.datetime.now().isoformat()
            _output_result(file_lock,
                           result_output_file,
                           {user_info['username']: result})
            st.driver.save_screenshot(os.path.join(screenshot_dir,
                                      f'{st.user_name}.png'))

        if logout:
            st.log_out()


def _get_user_list(file: str):
    users = list()
    file_ext = os.path.splitext(file)[1]
    with open(file, encoding='utf8') as f:
        if '.csv' == file_ext:
            csv_data = list(csv.DictReader(f))
            for d in csv_data:
                users.append(
                    dict(username=d['username'], password=d['password'])
                )
        elif file_ext in ('.yaml', '.yml'):
            users = yaml.safe_load(f)
    return users


if __name__ == "__main__":

    # 確認済み前提条件
    # moodle==4.2.7, 4.5.3
    # Python3.10.11

    parser = argparse.ArgumentParser(
        prog='main',
        description='e2e test for mcj-cloudhub using selenium',)

    parser.add_argument('accounts_file', type=str,
                        help='file path for test account list')
    parser.add_argument('lms_url', type=str,
                        help='lms url')
    parser.add_argument('selenium_executer', type=str,
                        help="executer for selenium")
    parser.add_argument('-b', '--browser', type=str, default="chrome",
                        help='browser to use (default: chrome)')
    parser.add_argument('-l', '--headless', type=bool, default=True,
                        help='exec in headless mode when True specified (default: True)')
    parser.add_argument('-i', '--tool_id', type=int, default=None,
                        help='tool id in lms for login to Jupyterhub with LTI')
    parser.add_argument('-c', '--course_name', type=str, default=None,
                        help='course_name in lms for login to Jupyterhub with LTI')
    parser.add_argument('-t', '--tool_name', type=str, default=None,
                        help='tool_name in lms for login to Jupyterhub with LTI')
    parser.add_argument('-s', '--src', type=str, default=None,
                        help="file path to execute in each user's single-user notebook server")
    parser.add_argument('-o', '--output_result', type=bool, default=True,
                        help="whether output result file (default: True)")

    args = parser.parse_args()
    users = _get_user_list(args.accounts_file)

    # LMS_TOOL_ID の指定があればこれを優先する
    # LMS_TOOL_ID の指定が無い場合、COURSE_NAME, TOOL_NAMEの指定が必須
    tool_id = args.tool_id
    course_name = args.course_name
    tool_name = args.tool_name

    if tool_id is None and (course_name is None and tool_name is None):
        raise ValueError('course_name and tool_name is required if tool_id is not specified.')

    exec_src = None
    if args.src is not None and os.path.isfile(args.src):
        with open(args.src, mode="r", encoding='utf8') as f:
            exec_src = f.read()

    result_file = None
    if args.output_result:
        date = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        result_file = os.path.join(os.path.dirname(__file__),
                                   'result', f'result_{date}.json')
        if os.path.isfile(result_file):
            os.remove(result_file)

    m = Manager()
    result_file_lock = m.Lock()
    p = Pool(len(users))
    for user in users:
        p.apply_async(main,
                      args=(user, args.lms_url, args.selenium_executer),
                      kwds=dict(tool_id=tool_id, tool_name=tool_name,
                                course_name=course_name, browser=args.browser,
                                headless=args.headless,
                                file_lock=result_file_lock,
                                result_output_file=result_file,
                                logout=True, exec_src=exec_src))

    print('Start subprocesses')
    p.close()
    p.join()
    print('All subprocesses done.')
