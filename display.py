import datetime
import time
from rich.live import Live
from rich.table import Table
from rich.console import Console
from rich import box
from rich.console import RenderGroup
from dataclasses import dataclass
import psutil
import json
import requests

@dataclass
class Info:
    rowID:             int
    roomID:             str
    startTime:          str
    endTime:            str
    autoRecord:         bool
    autoUpload:         bool
    liveStatus:         int
    lockStatus:         int
    uname:              str
    title:              str
    liveStartTime:      int
    recordStatus:       int
    recordStartTime:    int
    recordEndTime:      int
    decodeStatus:       int
    decodeStartTime:    int
    decodeEndTime:      int
    uploadStatus:       int
    uploadStartTime:    int
    uploadEndTime:      int
    needUpload:         bool
    state:              int

    @property
    def stateMap(self) -> str:
        if self.state == 0:
            return 'iinit'
        elif self.state == 1:
            return 'start'
        elif self.state == 2:
            return 'running'
        elif self.state == 3:
            return 'waiting'
        elif self.state == 4:
            return 'restart'
        elif self.state == 5:
            return 'decoding'
        elif self.state == 6:
            return 'decodeEnd'
        elif self.state == 7:
            return 'updateWait'
        elif self.state == 8:
            return 'updating'
        elif self.state == 9:
            return 'updateEnd'
        elif self.state == 10:
            return 'stop'

    @property
    def recordTimeMap(self) -> str:
        return cacUseTime(self.recordStartTime, self.recordEndTime)

    @property
    def decodeTimeMap(self) -> str:
        return cacUseTime(self.decodeStartTime, self.decodeEndTime)
    
    @property
    def uploadTimeMap(self) -> str:
        return cacUseTime(self.uploadStartTime, self.uploadEndTime)

    @property
    def liveStartTimeMap(self) -> str:
        return timeStamp2time(self.liveStartTime)

def timeStamp2time(ts):
    return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

def cacUseTime(startTime, endTime):
    if startTime > 0 and endTime != 0:
        return str((datetime.datetime.now() - datetime.datetime.fromtimestamp(startTime))).split('.')[0]
    elif startTime > 0:
        return str((datetime.datetime.fromtimestamp(endTime) - datetime.datetime.fromtimestamp(startTime))).split('.')[0]
    else:
        return 'nil'

def bytes2human(n):
     symbols = ('K','M','G','T','P','E','Z','Y')
     prefix = {}
     for i,s in enumerate(symbols):
         prefix[s] = 1 << (i + 1) * 10
     for s in reversed(symbols):
         if n >= prefix[s]:
             value = float(n) / prefix[s]
             return '%.1f%s' % (value,s)
     return '%.1fB' % float(n)

class Display():
    def __init__(self):
        self.console = Console(force_terminal=True, color_system='truecolor')
        self.console._environ['TERM'] = 'SMART'
        self.last_time = datetime.datetime.now()
        self.last_net_sent = 0.0
        self.last_net_recv = 0.0

    def generateInfo(self, rowID, liveInfo):
        return Info(
            rowID=rowID,
            roomID=liveInfo['RoomID'],
            startTime=liveInfo['StartTime'],
            endTime=liveInfo['EndTime'],
            autoRecord=liveInfo['AutoRecord'],
            autoUpload=liveInfo['AutoUpload'],
            liveStatus=liveInfo['LiveStatus'],
            lockStatus=liveInfo['LockStatus'],
            uname=liveInfo['Uname'],
            title=liveInfo['Title'],
            liveStartTime=liveInfo['LiveStartTime'],
            recordStatus=liveInfo['RecordStatus'],
            recordStartTime=liveInfo['RecordStartTime'],
            recordEndTime=liveInfo['RecordEndTime'],
            decodeStatus=liveInfo['DecodeStatus'],
            decodeStartTime=liveInfo['DecodeStartTime'],
            decodeEndTime=liveInfo['DecodeEndTime'],
            uploadStatus=liveInfo['UploadStatus'],
            uploadStartTime=liveInfo['UploadStartTime'],
            uploadEndTime=liveInfo['UploadEndTime'],
            needUpload=liveInfo['NeedUpload'],
            state=liveInfo['State']
        )

    def createInfoTable(self, liveInfos):
        infos = sorted(
            [self.generateInfo(rid, liveInfos[key]) for key, rid in
                zip(liveInfos.keys(), range(len(liveInfos)))],
            key=lambda i: i.state * 10 - i.rowID,
            reverse=True
        )
        table1 = Table(
            "行号", "房间ID", "主播", "直播标题", "直播状态", "开播时间", "录制时间", "转码用时", "上传用时", "当前状态",
            title="%s" % datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            box=box.SIMPLE
        )

        for info in infos:
            table1.add_row(
                str(info.rowID),
                info.roomID,
                info.uname,
                info.title,
                str(info.liveStatus),
                info.liveStartTimeMap,
                info.recordTimeMap,
                info.decodeTimeMap,
                info.uploadTimeMap,
                info.stateMap
            )

        table2 = Table(
            "CPU","Memory","NetSent","NetRecv",
            box=box.SIMPLE
        )

        time_now = datetime.datetime.now()
        now_recv = psutil.net_io_counters().bytes_recv
        now_sent = psutil.net_io_counters().bytes_sent

        table2.add_row(
            str(psutil.cpu_percent(None))+'%',
            str(psutil.virtual_memory().percent)+'%' + '  %s/%s' % (bytes2human(psutil.virtual_memory().used),bytes2human(psutil.virtual_memory().total)),
            bytes2human((now_sent-self.last_net_sent)/(time_now - self.last_time).total_seconds())+'/s',
            bytes2human((now_recv-self.last_net_recv)/(time_now - self.last_time).total_seconds())+'/s'
        )

        self.last_time = time_now
        self.last_net_sent = now_sent
        self.last_net_recv = now_recv

        return RenderGroup(
            table1,table2
        )

    def run(self):
        with Live(console=self.console, auto_refresh=False) as live:
            while True:
                r = requests.get("http://127.0.0.1:18080/api/infos")
                infos = json.loads(r.text)['RoomInfos']
                live.update(self.createInfoTable(infos), refresh=True)
                time.sleep(1)