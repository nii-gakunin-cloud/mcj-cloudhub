import os

TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S %Z'
TIMESTAMP_TIMEZONE = 'Asia/Tokyo'

c.CourseDirectory.course_id = os.environ.get('MOODLECOURSE')
c.Exchange.root = '/jupytershare/nbgrader/exchange'
c.Exchange.timestamp_format = TIMESTAMP_FORMAT
c.Exchange.timezone = TIMESTAMP_TIMEZONE
c.Exchange.path_includes_course = True
c.ExchangeCollect.timestamp_format = TIMESTAMP_FORMAT
c.ExchangeCollect.timezone = TIMESTAMP_TIMEZONE
c.ExchangeFetchAssignment.timestamp_format = TIMESTAMP_FORMAT
c.ExchangeFetchAssignment.timezone = TIMESTAMP_TIMEZONE
c.ExchangeFetch.timestamp_format = TIMESTAMP_FORMAT
c.ExchangeFetch.timezone = TIMESTAMP_TIMEZONE
c.ExchangeFetchFeedback.timestamp_format = TIMESTAMP_FORMAT
c.ExchangeFetchFeedback.timezone = TIMESTAMP_TIMEZONE
c.ExchangeList.timestamp_format = TIMESTAMP_FORMAT
c.ExchangeList.timezone = TIMESTAMP_TIMEZONE
c.ExchangeReleaseAssignment.timestamp_format = TIMESTAMP_FORMAT
c.ExchangeReleaseAssignment.timezone = TIMESTAMP_TIMEZONE
c.ExchangeRelease.timestamp_format = TIMESTAMP_FORMAT
c.ExchangeRelease.timezone = TIMESTAMP_TIMEZONE
c.ExchangeReleaseFeedback.timestamp_format = TIMESTAMP_FORMAT
c.ExchangeReleaseFeedback.timezone = TIMESTAMP_TIMEZONE
c.ExchangeSubmit.timestamp_format = TIMESTAMP_FORMAT
c.ExchangeSubmit.timezone = TIMESTAMP_TIMEZONE
c.ExecutePreprocessor.startup_timeout = 120
c.ExecutePreprocessor.timeout = 300
