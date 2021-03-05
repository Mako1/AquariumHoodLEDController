import sys, requests, json, threading, pigpio
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime, timedelta
from time import time, sleep

GPIO_NUM = 18
SWITCH_ON = "on"
SWITCH_OFF = "off"

PHASE_API_URL = 'https://api.sunrise-sunset.org/json?lat=36.7201600&lng=-4.4203400&date=today'
LED_FULL_ON = 255
LED_FULL_OFF = 0

DAY_START_ATTR = "civil_twilight_begin"
DAY_END_ATTR = "sunrise"
NIGHT_START_ATTR = "sunset"
NIGHT_END_ATTR = "civil_twilight_end"

StartAttr = ""
EndAttr = ""
Phases = ""
StartTime = 0
IsOn = 0
CurrCycle = 0
CurrTime = datetime.now()
ChangeFreq = 0

class setInterval :
    def __init__(self,interval,action) :
        self.interval=interval
        self.action=action
        self.stopEvent=threading.Event()
        thread=threading.Thread(target=self.__setInterval)
        thread.start()

    def __setInterval(self) :
        nextTime=time()+self.interval
        while not self.stopEvent.wait(nextTime-time()) :
            nextTime+=self.interval
            self.action()

    def cancel(self) :
        self.stopEvent.set()

def get_phases():
  response = requests.get(PHASE_API_URL)
  #print(response.json())
  r = json.loads(response.text)
  return r["results"]

def convert_time(time_str):
  return datetime.strptime(time_str, '%H:%M:%S %p')
  
def get_time_delta(start, end):
  #add 20 min to sunrise and sunset
  startTime = convert_time(start)
  endTime = convert_time(end) + timedelta(minutes=20)
  diff = endTime - startTime
  return round(diff.total_seconds() / 60)

def convert_time_to_24hour(timeObj):
  if Phases[StartAttr].rfind("P") > 0:
    return timeObj + timedelta(hours=12)
  else:
    return timeObj

def set_action(switch):
  global StartAttr, EndAttr, IsOn, CurrCycle
  if switch == "on":
    StartAttr = DAY_START_ATTR
    EndAttr = DAY_END_ATTR
    CurrCycle = LED_FULL_OFF
    IsOn = 1
  elif switch == "off":
    StartAttr = NIGHT_START_ATTR
    EndAttr = NIGHT_END_ATTR
    IsOn = 0
    CurrCycle = LED_FULL_ON

def action():
  global IsOn, CurrCycle
  if IsOn == 1:
    CurrCycle += 1
    set_duty_cycle(CurrCycle)
  else:
    CurrCycle -= 1
    set_duty_cycle(CurrCycle)

  print('action ! -> Freq : {:.1f}s - Cycle = {} - Time = {}'.format(time()-StartTime, CurrCycle, datetime.now().time()))

def set_duty_cycle(range):
  pi.set_PWM_dutycycle(GPIO_NUM, range)

def go():
  global StartTime, ChangeFreq
  phases = Phases
  delta = get_time_delta(phases[StartAttr], phases[EndAttr])
  deltaSec = delta * 60
  freq = round(deltaSec / 255, 4)
  ChangeFreq = freq
  print ("{0} to {1} = {2} minutes so change every {3} seconds".format(phases[StartAttr], phases[EndAttr], delta, freq))
  StartTime = time()
  inter = setInterval(freq, action)
  t = threading.Timer(deltaSec, inter.cancel)
  t.start()

argSwitch = ""
if len(sys.argv) > 1:
  argSwitch = sys.argv[1]
else:
  print("Option missing. Use 'on' for turning the light on. 'Off' for off.")
  quit()

Phases = get_phases()
set_action(argSwitch)

schedStart = convert_time(Phases[StartAttr])
schedStart = convert_time_to_24hour(schedStart)
scheduledStartDateTime = datetime.now().replace(hour=schedStart.hour, minute=schedStart.minute, second=schedStart.second, microsecond=0)
print("Start time: {}".format(scheduledStartDateTime))

pi = pigpio.pi()

sched = BlockingScheduler()
sched.add_job(go, 'date', run_date=scheduledStartDateTime)
sched.start()

