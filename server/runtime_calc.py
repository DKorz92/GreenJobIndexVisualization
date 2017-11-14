#!/usr/bin/python3.5
from jsonutils import readJSON
from dbConnector import connect
from scipy.optimize import linprog
from math import ceil

def calcTransOCC(msa,occCode,zetas):
    transProd = 1
    for occ in zetas[occCode].keys():
        if occ == "ges" or occ == occCode:
            continue
        if msa["values"][occ]>=1:
            transProd = transProd * (1-0.002*(zetas[occCode][occ]["zeta"]+1)*zetas[occCode]["ges"])
            #print(transProd)
    return 1-transProd
def calcTransEasy(msaCode,path):
    OCCs = readJSON(path+'ocspacepoints.json')
    MSAs = readJSON(path+'msaSpecDict.json')
    return calcTrans(MSAs[msaCode],OCCs,path)
def calcTransOCCEasy(msaCode,occCode,path):
    zetas = readJSON(path+'zetas.json')
    MSAs = readJSON(path+'msaSpecDict.json')
    return calcTransOCC(MSAs[msaCode],occCode,zetas)
def calcKOCC(msa,occCode,notSpecGreen,zetas):
    K = 0
    sum = 0
    for occ in zetas[occCode].keys():
        if occ == "ges" or occ == occCode or occ not in notSpecGreen:
            continue
        if msa["values"][occ]<1:
            K = K + zetas[occCode][occ]["prob"]
            sum = sum +1
    return K/sum



def industryReward(indCode,indReward,OCCs):
    connection = connect("bls_complete")
    cursor = connection.cursor()
    cursor.execute('''SELECT bls_nem_industries.`Industry title`, bls_nem_industries.`Industry code` , BLS_NEM.Occ_code, BLS_NEM.pc_occ_base , bls_nem_industries.`Industry type`
    FROM BLS_NEM, bls_nem_industries
    WHERE BLS_NEM.Ind_code = bls_nem_industries.`industry code` AND BLS_NEM.NEM_year = bls_nem_industries.NEM_Year AND BLS_NEM.Ind_Type = 0 AND bls_nem_industries.NEM_Year = 2014
    AND BLS_NEM.Ind_code = "''' + indCode + '"')
    result = cursor.fetchall()
    percs = {}
    for r in result:
        percs[r[2]]=r[3]
    for occ in OCCs:
        occ["act_reward"]=occ.get("act_reward",0) + percs.get(occ["code"],0)/100*indReward
        #print(occ["code"],occ["act_reward"],percs.get(occ["code"],0)/100)
    return OCCs
def calcNeeded(occNeeded,indOccBase):
    #print(occNeeded,indOccBase)
    for i in range(0,len(occNeeded)):
        occNeeded[i]=-occNeeded[i]
    for i in range(0,len(indOccBase)):
        for j in range(0,len(indOccBase[i])):
            indOccBase[i][j]= -indOccBase[i][j]
    c = []
    for i in range(0,len(indOccBase[0])):
        c = c + [1]
    res = linprog(c,indOccBase,occNeeded)
    if res.success == False:
        return {"suc":False}
    else:
        import math
        x = []
        for i in range(len(res.x)):
            x=x + [math.ceil(res.x[i])]
        return {"suc": True, "values":x}
def missingEmps(msaCode,occCode,year):
    connection = connect("bls_complete")
    cursor = connection.cursor()

    query = "SELECT OCC_CODE, TOT_EMP FROM BLS_OES WHERE AREA='"+msaCode+"' AND OCC_CODE ='"+occCode+"' AND OES_YEAR ="+year
    cursor.execute(query)
    #print(query)
    result = cursor.fetchall()
    if len(result) == 0:
        occData = 0
    else:
        if result[0][1] :
            occData = result[0][1]
        else:
            occData = 0

    cursor.execute("SELECT TOT_EMP FROM BLS_OES WHERE AREA='00000' AND OCC_CODE='"+occCode+"' AND OES_YEAR ="+year)
    result = cursor.fetchall()
    total_emp = result[0][0]

    cursor.execute("SELECT OCC_CODE, TOT_EMP FROM BLS_OES WHERE AREA='"+msaCode+"' AND OCC_CODE ='00-0000' AND OES_YEAR ="+year)
    result = cursor.fetchall()

    connection.close()

    #print(total_emp,result[0][1],occData,total_emp/137896660*result[0][1]-occData)

    return ceil(total_emp/137896660*result[0][1]-occData)

def missingEmpsSet(msaCode,occCodes,year):
    connection = connect("bls_complete")
    cursor = connection.cursor()

    occQueryWhere = "FALSE "
    for occ in occCodes:
        occQueryWhere = occQueryWhere +" OR OCC_CODE ='"+occ+"'"

    cursor.execute("SELECT OCC_CODE, TOT_EMP FROM BLS_OES WHERE AREA='"+msaCode+"' AND OES_YEAR ="+year +" AND ("+ occQueryWhere+")")
    #print(query)
    result = cursor.fetchall()
    occSet = {}
    for r in result:
        if r[1] and not r[1] == None:
            occSet[r[0]] ={"msa" : int(r[1])}
        else:
            occSet[r[0]] ={"msa" : 0}

    cursor.execute("SELECT OCC_CODE, TOT_EMP FROM BLS_OES WHERE AREA='00000'  AND OES_YEAR ="+year +" AND ("+ occQueryWhere+")")

    result = cursor.fetchall()
    for r in result:
        if not occSet.get(r[0]):
            occSet[r[0]] = {"msa" : 0}
        if r[1] and not r[1] == None:
            occSet[r[0]]["ges"] = int(r[1])
        else:
            occSet[r[0]]["ges"] = 0

    cursor.execute("SELECT OCC_CODE, TOT_EMP FROM BLS_OES WHERE AREA='"+msaCode+"' AND OCC_CODE ='00-0000' AND OES_YEAR ="+year)
    msaGes = int(cursor.fetchall()[0][1])

    connection.close()

    #print(total_emp,result[0][1],occData,total_emp/137896660*result[0][1]-occData)

    for occ in occCodes:
        if not occSet.get(occ):
            occSet[occ] = {"msa" : 0,"ges":0}
        missing = ceil(occSet[occ]["ges"]/137896660*msaGes-occSet[occ]["msa"])
        if missing < 0:
            missing = 0
        occSet[occ]["missing"]= missing

    return occSet

def MSAspecialiced(msaCode,OCCs,year,parent_path):
    connection = connect("bls_complete")
    cursor = connection.cursor()

    cursor.execute("SELECT OCC_CODE, TOT_EMP FROM BLS_OES WHERE AREA='"+msaCode+"' AND OES_YEAR ="+str(year))
    result = cursor.fetchall()


    #MSAs = readJSON(parent_path+'msas.json')
    spec = []
    for occ in OCCs:
        occData = -1
        for r in result:
            if occ["code"] == r[0]:
                if r[1]:
                    occData = r[1]+occ.get("act_reward",0)
                else:
                    occData = occ.get("act_reward",0)
                break
        if occData == -1:
            occData = occ.get("act_reward",0)
        spec = spec + [{"code": occ["code"], "local_quot": specialiced(137896660,occ["total_emp"].get(str(year),-1),result[0][1],occData), "green_flag":occ["green_flag"],"name":occ["name"]}]

    connection.close()
    return spec

def specialiced(gesamtArbeiterTotal,gesamtArbeiterOcc,gesamtArbeiterArea,gesamtArbeiterAreaOcc):
    if gesamtArbeiterAreaOcc==None or gesamtArbeiterArea==None or gesamtArbeiterOcc==None or gesamtArbeiterAreaOcc==0 or gesamtArbeiterArea==0 or gesamtArbeiterOcc==0:
        return 0
    localQuotient = (gesamtArbeiterAreaOcc/gesamtArbeiterArea)/(gesamtArbeiterOcc/gesamtArbeiterTotal)
    #print(localQuotient," =(",gesamtArbeiterAreaOcc,"/",gesamtArbeiterArea,")/(",gesamtArbeiterOcc,"/",gesamtArbeiterTotal,")")
    return localQuotient

def calcTrans(msa,OCCs,path):
    zetas = readJSON(path+'zetas.json')
    notSpecGreen = []
    greenSum = 0
    for occ in OCCs:
        if occ["green_flag"] == 1:
            greenSum = greenSum +1
            if msa["values"][occ["code"]]<1:
                notSpecGreen = notSpecGreen + [occ["code"]]
    zaehler = 0
    for occ in OCCs:
        transPot = calcTransOCC(msa,occ["code"],zetas)
        occ["transpot"] = transPot
        occ["K"] = calcKOCC(msa,occ["code"],notSpecGreen,zetas)
        occ["advantage"] = calcAdvantage(transPot,occ["code"],OCCs,zetas,greenSum)
        zaehler = zaehler +1
        #print(zaehler,"von",len(OCCs))
    for occ in OCCs:
        occ["green"] = calcAdvantage(occ["transpot"],occ["code"],OCCs,zetas,greenSum)
    #with open('ocspacepoints.json', 'w') as f:
         #json.dump(OCCs, f)
    return OCCs

def calcTransToIND(msa,ind,OCCs,path):
    zetas = readJSON(path+'zetas.json')
    notSpecInd = []
    indSum = 0
    for occ in OCCs:
        if ind[occ["code"]] >= 1:
            indSum = indSum +1
            if msa["values"][occ["code"]]<1:
                notSpecInd = notSpecInd + [occ["code"]]
    zaehler = 0
    for occ in OCCs:
        transPot = calcTransOCC(msa,occ["code"],zetas)
        occ["ind_transpot"] = transPot
        zaehler = zaehler +1
        #print(zaehler,"von",len(OCCs))
    #with open('ocspacepoints.json', 'w') as f:
         #json.dump(OCCs, f)
    return OCCs

def calcAdvantage(transPot,code,OCCs,zetas,N):
    ad = (1-transPot)
    for occ in OCCs:
        if occ["green_flag"] == 1:
            ad = ad +  occ["transpot"]*0.002*zetas[code][occ["code"]]["zeta"]
    return ad/N

def calcTransSpec(spec,OCCs,path):
    msa = {"values": {}}
    for occSpec in spec:
        msa["values"][occSpec["code"]] = occSpec["local_quot"]
    return msa

def calcGreen(spec,path):
    OCCs = readJSON(path+'ocspacepoints.json')
    OCCs = calcTrans(calcTransSpec(spec,OCCs,path),OCCs,path)
    greenSumm = 0
    greenGes = 0
    for occSpec in spec:
        occ = {}
        for o in OCCs:
            if o["code"]==occSpec["code"]:
                occ = o
                break
        if occ["green_flag"] == 1:
            if occSpec["local_quot"] >=1:
                greenSumm = greenSumm +1
            else:
                greenSumm = greenSumm + occ["transpot"]
            greenGes = greenGes +1
    return greenSumm/greenGes
def calcSuitability(msa,ind,path):
    OCCs = readJSON(path+'ocspacepoints.json')
    OCCs = calcTransToIND(calcTransSpec(msa,OCCs,path),ind,OCCs,path)
    indSumm = 0
    indGes = 0
    for occSpec in msa:
        occ = {}
        for o in OCCs:
            if o["code"]==occSpec["code"]:
                occ = o
                break
        if ind[occ["code"]] >= 1:
            if occSpec["local_quot"] >=1:
                indSumm = indSumm +1
            else:
                indSumm = indSumm + occ["ind_transpot"]
            indGes = indGes +1
    if indGes==0:
        return 0
    else:
        return indSumm/indGes

def calcSuitabilityWithCodes(msaCode,indCode):
    OCCs = readJSON('static/ocspacepoints.json')
    msa = MSAspecialiced(msaCode,OCCs,"2014","mysite/static/")
    from pre_calc import testIndSpec
    ind = testIndSpec(indCode)
    return calcSuitability(msa,ind,"static/")
