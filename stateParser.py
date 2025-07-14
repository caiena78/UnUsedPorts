
import re
import json

class stateParser:
    
    

    def pattern_match(self,pattern,data,none=False):
        match=re.findall(pattern,data)
        if match:
            return match
        if none == True:    
            return None
        return ""
    
   

    
    def __TimeSpanInterface(self,data):
        pattern=r'Last input ([0-9]{1,2}[ywdh][0-9]{1,2}[ywdh]|never|[0-9]{2}:[0-9]{2}:[0-9]{2}), output ([0-9]{1,2}[ywdh][0-9]{1,2}[ywdh]|never|[0-9]{2}:[0-9]{2}:[0-9]{2}), output hang never'
        timeSlices=re.findall(pattern,data)
        last_input=self.__ConvertToSec(timeSlices[0][0])
        last_output=self.__ConvertToSec(timeSlices[0][1])
        return (last_input,last_output)

    #Last input never, output never, output hang never
    #Last input 00:01:35, output 00:00:01, output hang never
    #
    #Last input 2y11w, output 2y11w, output hang never
   



    
    def __interface(self):
        return{
            "name":"",
            "description":"",
            "adminstate":"",            
            "connected":False,
            "Last_input":None,            
            "Last_Output":None,
            "LOutput":None,
            "mac_access":[],
            "mac_voice":[],
            "Trunk":False
        }    
    
    device=None  
    __TrunkData=None

    def __device(self):
         if "hostname" not in self.device:
            self.device={
                "hostname":"",                
                "sw_version":"",
                "model":[],
                "sn":[],
                "uptime":[],
                "interfaces":[]
            }
    

    def __timePattern(self):
        second = 1
        min=second * 60
        hour=60 * min
        day=24 * hour
        week=7 * day
        year=365 * day
        return [
            {
                "type":"years",
                "pattern": re.compile(r'([0-9]{1,2}) years'),
                "pattern2": re.compile(r'([0-9]{1,2})y'),
                "value": year
            },
            {
                "type":"weeks",
                "pattern": re.compile(r'([0-9]{1,2}) weeks'),
                "pattern2": re.compile(r'([0-9]{1,2})w'),
                "value":week
            },
            {
                "type":"days",
                "pattern": re.compile(r'([0-9]{1,2}) days'),
                "pattern2": re.compile(r'([0-9]{1,2})d'),
                "value":day
            },
            {
                "type":"hours",
                "pattern": re.compile(r'([0-9]{1,2}) hours'),
                "pattern2": re.compile(r'([0-9]{1,2})h'),
                "value":hour
            },
            {
                "type":"minutes",
                "pattern": re.compile(r'([0-9]{1,2}) minutes'),
                "pattern2": re.compile(r'([0-9]{1,2})m'),
                "value":min
            },
            {
                "type":"seconds",
                "pattern": re.compile(r'([0-9]{1,2}) seconds'),
                "pattern2": re.compile(r'([0-9]{1,2})s'),
                "value": second
            }
        ]


    #"2 years, 51 weeks, 5 days, 21 hours, 11 minutes"
    def __ConvertToSec(self,data):
        seconds=0
        timePattern=self.__timePattern()
        if data=='never':
            return None
        for item in timePattern:  
            match=re.findall(item["pattern"],data)
            if match:
                seconds=seconds+(int(match[0]) * item["value"])
                continue
            match=re.findall(item["pattern2"],data)
            if match:
                seconds=seconds+(int(match[0]) * item["value"])
        return seconds
        

        
        

    #'cisco ios software, ios-xe software, catalyst l3 switch software (cat3k_caa-universalk9-m), version 03.06.06e release software (fc1)'
    def parseShowVersion(self,data):
        lines=data.split('\n')
        self.__device()
        for line in lines:
            line=line.lower()
            if "cisco ios software, ios-xe software, catalyst l3 switch software" in line:
                pattern=r", version (.+) release software"
                match=re.findall(pattern,line)
                self.device["sw_version"]=match[0]  
                continue
            if "cisco ios software," in line:
                pattern=r", version (.+),"
                match=re.findall(pattern,line)
                self.device["sw_version"]=match[0]  
                continue
            if "cisco ios xe software, version" in line:
                pattern=r'cisco ios xe software, version (.+)'
                match=re.findall(pattern,line)
                self.device["sw_version"]=match[0]               
                continue
            if "uptime is" in line:
                pattern=r'^(.+) uptime is (.+)'
                match=re.findall(pattern,line)
                self.device["hostname"]=match[0][0]
                seconds=self.__ConvertToSec(match[0][1])
                self.device["uptime"].append(seconds)               
            if "switch uptime" in line:
                pattern=r'switch uptime\s+: (.+)'
                match=re.findall(pattern,line)
                if match:
                    seconds=self.__ConvertToSec(match[0])
                    self.device["uptime"].append(seconds)
            if "model number" in line:
                pattern=r'model number\s+:(.+)'
                match=re.findall(pattern,line)
                self.device['model'].append(match[0])                            
            if "system serial number" in line:
                pattern=r'system serial number\s+:(.+)'
                match=re.findall(pattern,line)
                self.device['sn'].append(match[0])

    def __isTrunk(self, interface):
        if self.__TrunkData == None:
            return None
        search=interface.replace("GigabitEthernet","Gi").replace("Port-channel","Po").replace("TenGigabitEthernet","Ten")
        if search in self.__TrunkData:
            return True
        return False
            

    #interface Data 
    def __init__(self, interfaceData=None,showversion=None,TrunkData=None,macAddress=None):                
        if interfaceData != None:
            self.paserInterface(interfaceData)
        if showversion != None:
            self.parseShowVersion(showversion)
        if macAddress != None:
            pass
        if TrunkData!=None:
            self._TrunkData=TrunkData
            pass


    
    def paserInterface(self,interfaceData):
        statecfg=interfaceData.split("\n")
        cnt=-1
        self.__device()        
        for line in statecfg:                        
            if line[:15] == "GigabitEthernet" or line[:12] == "Port-channel" or line[:20] == "FortyGigabitEthernet"  or line[:18] == "TenGigabitEthernet" :
                pattern=r'(Port-channel[0-9]{1,2}|GigabitEthernet[0-9]{1,2}/[0-9]/[0-9]{1,2}|GigabitEthernet[0-9]{1,2}/[0-9]{1,2}|FortyGigabitEthernet[0-9]{1,2}/[0-9]/[0-9]{1,2}|TenGigabitEthernet[0-9]{1,2}/[0-9]/[0-9]{1,2}) is (down|up|administratively down), line protocol is (down|up) \((.+)\)'
                data=re.findall(pattern,line)                
                if data:                    
                    cnt=cnt+1                   
                    self.device["interfaces"].append(self.__interface())                   
                    self.device["interfaces"][cnt]["name"]=data[0][0]
                    self.device["interfaces"][cnt]["adminstate"]=data[0][1]                    
                    if data[0][3].strip() == 'connected':
                        self.device["interfaces"][cnt]["connected"]=True  
                    #CMA Added
                    self.device["interfaces"][cnt]["Trunk"]=self.__isTrunk(self.device["interfaces"][cnt]["name"])
            if cnt==-1:
                continue
            if "Last input" in line[:14]:               
                timedata=self.__TimeSpanInterface(line)
                if timedata:
                    self.device["interfaces"][cnt]["Last_input"]=timedata[0]
                    self.device["interfaces"][cnt]["Last_Output"]=timedata[1]                 
            if "Description:" in line:
                    self.device["interfaces"][cnt]["description"]=line[14:].strip()





