from os.path import dirname
from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_handler, intent_file_handler
from mycroft.util.log import getLogger
from mycroft.util.log import LOG
from mycroft.audio import wait_while_speaking
from mycroft.skills.context import adds_context, removes_context
from mycroft.api import DeviceApi

import json
import random
import datetime
import time
import threading
import sys
import os
from pathlib import Path
from threading import Timer


class NewThread:
    id = 0
    idStop = False
    next_interval = 0
    idThread = threading.Thread

__author__ = 'PCWii'

# Logger: used for debug lines, like "LOGGER.debug(xyz)". These
# statements will show up in the command line when running Mycroft.
LOGGER = getLogger(__name__)


# The logic of each skill is contained within its own class, which inherits
# base methods from the MycroftSkill class with the syntax you can see below:
# "class ____Skill(MycroftSkill)"
class C25kSkill(MycroftSkill):

    # The constructor of the skill, which calls Mycroft Skill's constructor
    def __init__(self):
        super(C25kSkill, self).__init__(name="C25kSkill")
        # Initialize settings values
        self._is_setup = False
        self.workout_mode = NewThread
        self.schedule_location = ""
        self.interval_position = 0
        self.progress_week = 1
        self.progress_day = 1

    # This method loads the files needed for the skill's functioning, and
    # creates and registers each intent that the skill uses
    def initialize(self):
        self.load_data_files(dirname(__file__))
        #  Check and then monitor for credential changes
        self.settings.set_changed_callback(self.on_websettings_changed)
        self.on_websettings_changed()
        # Todo Add / update the following to the websettings for tracking
        location = os.path.dirname(os.path.realpath(__file__))
        self.schedule_location = location + '/./schedules/'  # get the current skill parent directory path
        self.interval_position = 0
        self.progress_week = 1
        self.progress_day = 1

    def on_websettings_changed(self):  # called when updating mycroft home page
        self._is_setup = False
        LOG.info("Websettings Changed!")
        self._is_setup = True

    def load_file(self, filename):  # loads the workout file json
        with open(filename) as json_file:
            data = json.load(json_file)
            return data

    def end_of_interval(self):
        LOG.info('Interval Completed!')
        self.interval_position += 1

    def end_of_workout(self):
        LOG.info('Workout Ended!')
        # Todo workout completed housekeeping
        self.halt_workout_thread()

    def init_workout_thread(self):  # creates the workout thread
        self.workout_mode.idStop = False
        self.workout_mode.id = 101
        self.workout_mode.idThread = threading.Thread(target=self.do_workout_thread,
                                                      args=(self.workout_mode.id,
                                                            lambda: self.workout_mode.idStop))
        self.workout_mode.idThread.start()

    def halt_workout_thread(self):  # requests an end to the workout
        self.workout_mode.id = 101
        self.workout_mode.idStop = True
        self.workout_mode.idThread.join()

    def do_workout_thread(self, my_id, terminate):  # This is an independant thread handling the workout
        LOG.info("Starting Workout with ID: " + str(my_id))
        active_schedule = self.load_file(self.schedule_location + "c25k.json")
        this_week = active_schedule["weeks"][self.progress_week - 1]
        this_day = this_week["day"][self.progress_day - 1]
        all_intervals = this_day["intervals"]
        last_interval = len(all_intervals)
        LOG.info('Last Interval = ' + str(last_interval))
        interval_list = enumerate(all_intervals)
        try:
            for index, value in interval_list:
                this_interval = json.dumps(all_intervals[index])
                for key in all_intervals[index]:
                    this_duration = all_intervals[index][key]
                LOG.info("Workout Interval Length: " + str(this_duration) + " seconds")
                LOG.info("Workout underway at step: " + str(index + 1) + "/" + str(last_interval) +
                         ", " + str(this_interval))
                notification_threads = []  # reset notification threads
                if index == (last_interval - 1):  # Check for the last interval
                    # Todo add Last interval threads here
                    notification_threads.append(Timer(this_duration, self.end_of_workout))
                    LOG.info('Last Interval workout almost completed!')
                else:
                    # Todo add motivation threads here
                    if this_duration >= 30:  # Motivators only added if interval length is greater than 30 seconds
                        notification_threads.append(Timer(int(this_duration/2), self.speak_motivation))
                        notification_threads.append(Timer(int(this_duration - 10), self.speak_transition))
                    notification_threads.append(Timer(int(this_duration - 5), self.speak_countdown, 5))
                    notification_threads.append(Timer(this_duration, self.end_of_interval))
                for each_thread in notification_threads:
                    each_thread.start()
                LOG.info("waiting for interval to complete!")
                while (index == self.interval_position) and not terminate():  # wait while this interval completes
                    time.sleep(1)
                    # This is a do nothing loop while the workout proceeds
                if terminate():
                    for each_thread in notification_threads:
                        each_thread.cancel()
                        self.interval_position = 0
                    if index != (last_interval - 1):
                        LOG.info('Workout was terminated!')
                    else:
                        LOG.info('Workout was Completed!')
                    break
            # Todo add workout canceled housekeeping here
        except Exception as e:
            LOG.error(e)  # if there is an error attempting the workout then here....
            for each_thread in notification_threads:
                each_thread.cancel()

    def speak_motivation(self):
        self.speak_dialog('motivators', expect_response=False)

    def speak_transition(self):
        self.speak_dialog('transitions', expect_response=False)

    def speak_countdown(self, count):
        for i in range(1, count+1):
            self.speak_dialog('countdown', data={"value": str(i)}, expect_response=False)

    @intent_handler(IntentBuilder("BeginWorkoutIntent").require("RequestKeyword").require('WorkoutKeyword').build())
    def handle_begin_workout_intent(self, message):
        self.init_workout_thread()
        LOG.info("The workout has been Started")

    @intent_handler(IntentBuilder('StopWorkoutIntent').require('StopKeyword').require('WorkoutKeyword').build())
    def handle_stop_workout_intent(self, message):
        self.halt_workout_thread()
        LOG.info("The workout has been Stopped")

    def stop(self):
        pass


# The "create_skill()" method is used to create an instance of the skill.
# Note that it's outside the class itself.
def create_skill():
    return C25kSkill()
