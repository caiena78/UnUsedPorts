from getpass import getpass
from tkinter import NO
from stateParser import * 
from netmiko import ConnectHandler 
import os
import re
import logging




def startlogging(level):
    formatter=('%(asctime)s-%(name)s-%(levelname)s-%(message)s')
    logging.basicConfig(filename="logs.log",filemode='w',level=level,format=formatter)
    logging.info("Started")

def convertSeconds(seconds):
    if seconds == None:
        return "NONE"
    #return seconds
    sec = 1
    min = 60 * sec
    hour = 60 * min
    day = 24 * hour
    week=day * 7
    month=day*30
    year= day * 365 
    output=""
    y=0
    # m=0
    w=0
    d=0
    h=0
    mi=0
    s=0
    if int(seconds / year) > 0:        
        y = int((seconds / year))
        seconds = seconds - ( y * year)
    if int(seconds/week) > 0:
        w = int(seconds/week)
        seconds = seconds - ( w * year)
    if int(seconds / day) > 0:
        d=int(seconds / day)
        seconds = seconds - (d * day)
    if int(seconds / hour) > 0:
        h=int(seconds / hour)
        seconds = seconds - (h * hour)
    if int(seconds / min) > 0:
        mi=int(seconds / min)
        seconds = seconds - (mi * min)
    if  seconds > 0:
        s=seconds
    output="%sY %sW %sD %sH %sm %sS" % (y,w,d,h,mi,s)             
    return output





# Returns all parmaters for netmiko to login to the device
def ios(ip,user,password,enable=""):    
    device={
        'device_type': 'cisco_ios',
        'host':   ip,
        'username': user,
        'password': password,
        'port' : 22,          # optional, defaults to 22   
        'conn_timeout' : 40,
        'global_delay_factor': 30,
        'secret':enable,  
        "session_log": 'netmiko_session.log'
    }    
    logging.info(device)
    return device


def isEnable(device):
     with  ConnectHandler(**device) as net_connect:        
       return net_connect.check_enable_mode()       
    
def enableMode(device):
    with  ConnectHandler(**device) as net_connect:   
        net_connect.enable()
        isEnabled=net_connect.check_enable_mode()
    return isEnabled

def sendCMD(device,command):
    with  ConnectHandler(**device) as net_connect:                
        if net_connect.check_enable_mode() == False:
            net_connect.enable()
        Data = net_connect.send_command(command,use_textfsm=False)        
    return Data

# sends configure commands to the device, example ["int gi1/0/1","desc TESTING"] 
def sendConfig(device,commands:list):
    Data="NA"    
    logging.info("Sending Update")
    logging.info("Device:%s" % device['host'] )
    logging.info("Sending CFG: %s" % commands)   
    with  ConnectHandler(**device) as net_connect:  
          net_connect.enable()              
          Data=""          
          Data = net_connect.send_config_set(commands)               
    return Data     

# sends the device "show int"    
def showInt(device):
    data=sendCMD(device,"show int")
    return data

# sends the device show version
def showVersion(device):
    data=sendCMD(device,"show version")
    return data

#sends the device "show in trunk"
def showIntTrunk(device):
    data=sendCMD(device,"show int trunk")
    return data

#writes the ports that can be disabled to a file
def disableList(fname,data):
    
    fname=os.path.join(os.getcwd(),"disable",fname)
    with open(fname,"a") as w:
        w.write(data+"\n")

# get's the switch or blade number from the interface
def switchNumber(interface):
    pattern=r'GigabitEthernet[0-9]/[0-9]{1,2}'
    match=re.findall(pattern,interface)
    if match:
        # return 1 if its an older switch that only has one it the stack like a 3560
        return "1"
    pattern=r'GigabitEthernet([0-9]{1})/[0-9]/[0-9]{1,2}'
    match=re.findall(pattern,interface)
    return match[0]

def createInventory():
    fname="inventory.csv"
    if os.path.exists(fname):
        os.remove(fname)
    with open(fname,"w") as f:
        headers="ip,hostname,model,version,sn,switch_cnt,Total_Interfaces,Unused_Interfaces"
        f.write(headers+"\n")
    

def inventory(ip:str,switchobj:stateParser,unusedIfaceCNT=0):
    fname="inventory.csv"
    model=",".join(switchobj.device["model"])
    version=switchobj.device["sw_version"]
    sn=",".join(switchobj.device['sn'])
    switchCNT=len(switchobj.device["model"])
    hostname=switchobj.device["hostname"]
    iface_cnt=len(switchobj.device['interfaces'])
    with open(fname,"a") as f:
        f.write(f'\"{ip}\",\"{hostname}\",\"{model}\",\"{version}\",\"{sn}\",\"{switchCNT}\",\"{iface_cnt}\",\"{unusedIfaceCNT}\"\n')

             
         
    

# mode options are as follows
# 0 = no action
# 1 = Create file
# 2 = update description with "!" at the begining
# 3 = shutdown port 
def shutdown(device,mode,disabletime):
    if mode == 0:
        return
    interfaceData=showInt(device)
    versionData=showVersion(device)
    TrunkData=showIntTrunk(device)
    x=stateParser(interfaceData,versionData,TrunkData)    
    sec = 1
    min = 60 * sec
    hour = 60 * min
    day = 24 * hour      
    switchList=""
    cnt=0
    unusedIfaceCNT=0
    # loop through all the uptime on the switches and skip any that have not been up long enough
    for uptime in x.device['uptime']:
        cnt = cnt + 1
        if uptime < disabletime:            
            continue
        else:
            switchList=switchList+str(cnt)
    for interface in x.device['interfaces']:
        #skip side modules
        if "/1/" in interface['name']:
            continue
        #skip interfaces with !#! in the description
        if "!#!" in interface['description']:
            continue
        #skip any port-channel's    
        if "Port-channel" in interface['name']:
            continue
        #skip any FortyGigabitEthernet
        if "FortyGigabitEthernet" in interface['name']:
            continue
        #skip any TenGigabitEthernet
        if "TenGigabitEthernet" in interface['name']:
            continue
        if interface['Trunk']==True:
            #Safty skip trunk just in case
            continue
        switchNum=switchNumber(interface['name']) 
        if switchNum not in switchList:
            #print("Skipping Switch:%s" % switchNum)
            continue
        if interface['adminstate']=="administratively down":
            unusedIfaceCNT=unusedIfaceCNT+1
            if "!" in interface['description']:
                Action(device,interface,1,device['host'])
                continue
            if mode==3:
                # update the description and don't shutdown the port because its alread disabled.
                Action(device,interface,2,device['host'])
            else:
                Action(device,interface,mode,device['host'])
            continue
        if interface['connected']==False and (interface['Last_input'] == None or interface['Last_input'] > disabletime):
            unusedIfaceCNT=unusedIfaceCNT+1
            Action(device,interface,mode,device['host'])
    inventory(device['host'],x,unusedIfaceCNT)  # added to take inventory

# mode options are as follows
# 0 = no action
# 1 = Create file
# 2 = update description with "!" at the begining
# 3 = shutdown port 
def Action(device,interface,mode,ip):
    if mode==0:
        return
    if mode >= 1:
        data="%s,description:%s,Last_input:%s" % (interface['name'],interface['description'].strip(),convertSeconds(interface['Last_input']))
        fname="%s.txt" % ip.replace(".","_")
        disableList(fname,data)
    if mode==2:
        updateCMD=[]
        updateCMD.append("int %s" % interface['name'])
        if len(interface['description'].strip()) > 0:
            data="description ! " + interface['description']
        else:
            data="description !"
        updateCMD.append(data)
        # Diable the switch update
        sendConfig(device,updateCMD)
    if mode==3:
        updateCMD=[]
        updateCMD.append("int %s" % interface['name'])
        if len(interface['description'].strip()) > 0:
            data="description ! " + interface['description']
        else:
            data="description !"
        updateCMD.append(data)
        updateCMD.append("shutdown")        
        sendConfig(device,updateCMD)
        

def cleanUpDirectory():
    try:
        
        path=os.path.join(os.getcwd(),"disable")
        if os.path.exists(path):
            os.makedirs(path)
            return
        dirList=os.listdir(path)
        for item in dirList:
            if item.endswith(".txt"):
                os.remove(os.path.join(path,item))
    except Exception as err:
        logging.error(err)



def getLogin():
    user=None
    pwd=None
    enable=None
    if os.environ.get("CISCO_SRV_ACCOUNT",False):
        user=os.environ["CISCO_SRV_ACCOUNT"]
    else:
        user=input("Please Enter a Username: ") or None
    
    if os.environ.get("CISCO_SRV_PWD",False):
        pwd=os.environ["CISCO_SRV_PWD"]    
    else:
        pwd=getpass("Please Enter your password: ") or None

    if os.environ.get("CISCO_ENABLE_PWD",False):        
        enable=os.environ["CISCO_ENABLE_PWD"]
    else: 
        enable=getpass("Please Enter your enable password: ") or "enable" 
    if user == None or pwd==None:
        raise Exception('User Or Password not set')
    return user,pwd,enable



startlogging(logging.ERROR)
#startlogging(logging.DEBUG)   #####DEBUGING####
cleanUpDirectory()
createInventory()
user,pwd,enable=getLogin()
try:

    if os.path.exists("disable.txt"):
        os.remove("disable.txt")
    with open("list.json","r") as w:
        deviceList=json.load(w)
    for switch in deviceList:        
        try:
            if switch['enabled']== True:   
                print(switch["ip"])  
                device=ios(switch["ip"],user,pwd,enable)
                shutdown(device,switch["Shutdown"],switch["disabletime"])        
        except Exception as e:
            logging.error(e)
except Exception as err:
    logging.error(err)
    raise err










