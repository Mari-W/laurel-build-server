import json

from sqlalchemy import Column, Integer, DateTime, String, Boolean, Text

from server.database import database


class Build(database.Model):
    __tablename__ = 'build'

    id = Column(Integer, primary_key=True)

    start = Column(DateTime, nullable=False)
    end = Column(DateTime, nullable=False)

    course = Column(String(128), nullable=False)
    exercise = Column(String(128))
    student = Column(String(64), nullable=False)

    logs = Column(Text, nullable=False)
    failure = Column(Boolean, nullable=False)

    @property
    def duration(self):
        diff = self.end - self.start
        return f"{diff.seconds}.{str(diff.microseconds)[0:1]}s"

    @property
    def logs_as_list(self):
        return [log for log in json.loads(self.logs) if log]
