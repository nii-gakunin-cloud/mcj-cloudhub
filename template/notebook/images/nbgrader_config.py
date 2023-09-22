import os
import sys

# sys.stderr.write(str(os.environ) + "\n")

if os.environ.get('MOODLECOURSE'):
    if os.environ.get('COURSEROLE') != None:
        c.Exchange.root = '{{share_directory_root}}/nbgrader/exchange'
        c.Exchange.timestamp_format = '%Y-%m-%d %H:%M:%S %Z'
        c.Exchange.timezone = 'JST'
        c.ExchangeCollect.timestamp_format = '%Y-%m-%d %H:%M:%S %Z'
        c.ExchangeCollect.timezone = 'JST'
        c.ExchangeFetchAssignment.timestamp_format = '%Y-%m-%d %H:%M:%S %Z'
        c.ExchangeFetchAssignment.timezone = 'JST'
        c.ExchangeFetch.timestamp_format = '%Y-%m-%d %H:%M:%S %Z'
        c.ExchangeFetch.timezone = 'JST'
        c.ExchangeFetchFeedback.timestamp_format = '%Y-%m-%d %H:%M:%S %Z'
        c.ExchangeFetchFeedback.timezone = 'JST'
        c.ExchangeList.timestamp_format = '%Y-%m-%d %H:%M:%S %Z'
        c.ExchangeList.timezone = 'JST'
        c.ExchangeReleaseAssignment.timestamp_format = '%Y-%m-%d %H:%M:%S %Z'
        c.ExchangeReleaseAssignment.timezone = 'JST'
        c.ExchangeRelease.timestamp_format = '%Y-%m-%d %H:%M:%S %Z'
        c.ExchangeRelease.timezone = 'JST'
        c.ExchangeReleaseFeedback.timestamp_format = '%Y-%m-%d %H:%M:%S %Z'
        c.ExchangeReleaseFeedback.timezone = 'JST'
        c.ExchangeSubmit.timestamp_format = '%Y-%m-%d %H:%M:%S %Z'
        c.ExchangeSubmit.timezone = 'JST'

        c.Exchange.path_includes_course = True

        c.CourseDirectory.course_id = os.environ.get('MOODLECOURSE')
        # increase timeout to 120 seconds
        c.ExecutePreprocessor.startup_timeout = 120
        # increase timeout to 300 seconds
        c.ExecutePreprocessor.timeout = 300

        c.FormgradeApp.mathjax_url = 'static/components/MathJax/MathJax.js'
        c.HTMLExporter.mathjax_url = 'static/components/MathJax/MathJax.js'

        if os.environ.get('COURSEROLE') == 'Instructor':
            c.CourseDirectory.root = os.environ.get('HOME') + '/nbgrader/' + os.environ.get('MOODLECOURSE')
#        if os.environ.get('COURSEROLE') == 'Learner':
#            c.Exchange.path_includes_course = True

