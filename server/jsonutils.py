#!/usr/bin/python3.5
import json
import MySQLdb

occFile = 'ocspacepoints.json'
msaFile = 'msas.json'

#_____________________________________________________________________________________________________________________________
#HELPERS START
def connect(name):
    connection = MySQLdb.connect(
        host="foaly.mysql.pythonanywhere-services.com",
        db="Foaly$"+name,
        user="Foaly", passwd="lealea333"
        )
    return connection


def readJSON(path):
    with open(path, 'r') as data_file:
        data_loaded = json.load(data_file)
    return data_loaded

def isGreen(data):
    connection = connect("o_net")
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM occupation_data, green_occupations WHERE occupation_data.onetsoc_code = green_occupations.onetsoc_code AND occupation_data.onetsoc_code = '"+str(data["code"])+".00'")
    result = cursor.fetchall()
    if len(result) >0:
        data["green_flag"]=1
    else:
        data["green_flag"]=0
    connection.close()

def checkGreenFlagWithDepth(data):
    connection = connect("o_net")
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM occupation_data, green_occupations WHERE occupation_data.onetsoc_code = green_occupations.onetsoc_code AND occupation_data.onetsoc_code = '"+str(data["code"])+".00'")
    result = cursor.fetchall()
    isGreen = 0
    if len(result) >0:
        isGreen=1
    cursor.execute('''SELECT *
                    FROM occupation_data, green_occupations
                    WHERE occupation_data.onetsoc_code = green_occupations.onetsoc_code
                        AND occupation_data.onetsoc_code LIKE "'''+str(data["code"])+'''.%"
                        AND NOT occupation_data.onetsoc_code = "'''+str(data["code"])+'''.00" ''')
    result = cursor.fetchall()
    depthGreen = len(result)
    print(data["code"],"has greenflag",isGreen,"and has",depthGreen,"green under occupations")
    connection.close()

def getName(data):
    connection = connect("o_net")
    cursor = connection.cursor()
    cursor.execute("SELECT title FROM occupation_data WHERE  onetsoc_code = '"+str(data["code"])+".00'")
    result = cursor.fetchall()
    if len(result) == 0:
        data["name"]=""
    else:
        data["name"]=result[0][0]
    connection.close()

def checkGreen():
    data_loaded = readJSON('static/ocspacepoints.json')
    for data in data_loaded:
        getName(data)
    with open('static/ocspacepoints.json', 'w') as f:
         json.dump(data_loaded, f)


def checkGreens(path):
    MSAs = readJSON(path+'msas.json')
    for msa in MSAs:
        green = msa.get("greenIndex",-1)
        if green <0 or green>1:
            msa["greenIndex"]=calcGreen(msa["code"],path)
    with open(path+'msas.json', 'w') as f:
         json.dump(MSAs, f)

#HELPERS END
#_______________________________________________________________________________________________________________________________

#_______________________________________________________________________________________________________________________________
#PRECALC START

year = 0
def getYearValue(d):
    for y in d.get("overYear",[]):
        if y["year"]==year:
            return (-1)*y["value"]
    return 0
def getRankValue(d):
    for y in d.get("overYear",[]):
        if y["year"]==year:
            return y["rank"]
    return 0

def createRank():
    MSAs = readJSON("static/msas.json")
    global year
    for y in range(2004,2016):
        year = y
        MSAs = sorted(MSAs,key=getYearValue)
        for i in range(len(MSAs)):
            if not MSAs[i].get("overYear",[]) == []:
                for ys in MSAs[i]["overYear"]:
                    if ys["year"]== year:
                        ys["rank"]= i
                        break
    with open('static/msas.json', 'w') as f:
        json.dump(MSAs, f)
def calcRank(value,projYear):
    MSAs = readJSON("mysite/static/msas.json")
    global year
    year = projYear
    MSAs = sorted(MSAs,key=getYearValue)
    for i in range(len(MSAs)):
        if not MSAs[i].get("overYear",[]) == []:
            for ys in MSAs[i]["overYear"]:
                if ys["year"]== year and ys["value"]<value:
                    return i
    return -1

def fillMSAWithSpec():
    OCCs = readJSON('mysite/static/ocspacepoints.json')
    MSAs = readJSON('mysite/static/msas.json')
    for msa in MSAs:
        spec = []
        for occ in OCCs:
            print("MSA: ",msa["name"],"Occupation:",occ["code"])
            s = specialiced(msa["code"],occ["code"])
            print("local quotient bei",s)
            spec = spec + [{"code": occ["code"],"quotient": s}]
        msa["specialication"]=spec
    with open('mysite/static/msas.json', 'w') as f:
        json.dump(MSAs, f)


def countSpecForMSA():
    msaSpecs = readJSON('static/msaSpec.json')
    print(msaSpecs)
    for spec in msaSpecs:
        count = 0
        aver = 0
        for value in spec["values"]:
            if value["local_quot"]>=1:
                count = count +1
                aver = aver + value["local_quot"]
        print("For MSA",spec["name"],count,"specialications found with average",aver/count)


#PRECALC END
#_____________________________________________________________________________________________________________________________________________

#_____________________________________________________________________________________________________________________________________________
#RUNTIME START

def calcGreen(code,path):
    OCCs = readJSON(path+'ocspacepoints.json')
    MSAs = readJSON(path+'msaSpecDict.json')
    OCCs = runtime_calc.calcTrans(MSAs[code],OCCs,path)
    greenSumm = 0
    greenGes = 0
    for occCode in MSAs[code]["values"].keys():
        occ = {}
        for o in OCCs:
            if o["code"]==occCode:
                occ = o
                break
        if occ["green_flag"] == 1:
            if MSAs[code]["values"][occ["code"]] >=1:
                greenSumm = greenSumm +1
            else:
                greenSumm = greenSumm + occ["transpot"]
            greenGes = greenGes +1
    return greenSumm/greenGes

def calcAllGreens(path,von,bis):
    years = range(2003,2016)
    aktYear = years[len(years)-1]
    MSAs = readJSON(path+'msas.json')
    zaehler = von
    for i in range(von,bis):
        for y in years:
            msa = MSAs[i]
            #green = msa.get("greenIndex",calcGreen(msa["code"],path))
            green = calcGreen(msa["code"],path)
            msa["greenIndex"]=green
            zaehler = zaehler+1
            print(zaehler,"von",bis)
    with open(path+'msas.json', 'w') as f:
         json.dump(MSAs, f)

#RUNTIME END
#__________________________________________________________________________________________________________________________________________
#MSAspecialiced("0040")
