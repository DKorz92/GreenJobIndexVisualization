#!/usr/bin/python3.5
import json
from dbConnector import connect
from jsonutils import readJSON
from runtime_calc import MSAspecialiced
from runtime_calc import specialiced

g_path = "../static/"
g_occFile = g_path + "ocspacepoints.json"
g_msaFile = g_path + 'msas.json'
g_specFile = g_path + 'msaSpec.json'
g_testFile = g_path + "test.json"
g_specDictFile = g_path + 'msaSpecDict.json'
g_industryFile = g_path + "industries.json"

def prepAdvancedIndustries():
    aI = readJSON(g_path+"advanced_industries.json")
    for i in aI:
        addDigits = 6-int(i["Code_Level"])
        i["Industry_Code"] = i["Industry_Code"]*(pow(10,addDigits))
    with open(g_path+"advanced_industries.json", 'w') as f:
         json.dump(aI, f)

def writeAdvanced():
    advanced = readJSON(g_path+"advanced_industries.json")
    industries = readJSON(g_path+"industries.json")
    for i in industries.keys():
        found = False
        for a in advanced:
            if str(i) == str(a["Industry_Code"]):
                industries[i]["advanced_flag"] = 1
                print(i+" 1")
                found = True
                break
        if not found:
            industries[i]["advanced_flag"] = 0
            print(i+" 0")
    with open(g_path+"industries.json", 'w') as f:
         json.dump(industries, f)


def calculateTotEmpMSA():
    """
    Calculate the total employes for each MSA and store it in the msas.json file
    Uses: Nothing
    """

    MSAs = []
    connection = connect("bls_complete")
    cursor = connection.cursor()
    cursor.execute("SELECT AREA,AREA_NAME, SUM(TOT_EMP) AS GESAMT FROM BLS_OES GROUP BY AREA")
    result = cursor.fetchall()
    for r in result:
        MSAs = MSAs + [{"name": str(r[1]), "code": str(r[0]), "total_emp": int(r[2])}]
        print(r[0],"hat ingesamt",r[1],"Arbeiter")
    with open(g_msaFile, 'w') as f:
        json.dump(MSAs, f)
    connection.close()

def writeSpecJSON(von,bis):
    """
    Reads existing data from ocspacepoints.json and stores the specialication for each MSA and OCCs
    Uses: MSAspecialiced
    """

    OCCs = readJSON(g_occFile)
    connection = connect("bls_complete")
    cursor = connection.cursor()
    cursor.execute("SELECT DISTINCT AREA, AREA_NAME FROM BLS_OES")
    result = cursor.fetchall()
    spec = []
    years = range(2003,2015)
    counter = 0
    if(bis<0):
        bis = len(result)
    for i in range(bis):
        r = result[i]
        areaCode = r[0]
        specValues = MSAspecialiced(areaCode,OCCs,"2015",g_path)
        yearValues = []
        for y in years:
            yearValues = yearValues + [{"year": y,"values": MSAspecialiced(areaCode,OCCs,str(y),g_path)}]
        spec = spec + [{"name": r[1], "code": areaCode, "values": specValues,"yearValues":yearValues}]
        counter = counter +1
        print(str(counter) +" von "+str(len(result)))
    with open(g_testFile, 'w') as f:
         json.dump(spec, f)
    connection.close()

def reStructSpec():
    """
    Function to give the msaSpec.json file a easier structure
    Uses: Nothing
    """
    MSAs = readJSON(g_specFile)
    specs = {}
    for msa in MSAs:
        specs[msa["code"]] = {}
        specs[msa["code"]]["name"]=msa["name"]
        specs[msa["code"]]["values"] = {}
        for value in msa["values"]:
            specs[msa["code"]]["values"][value["code"]] = value["local_quot"]
    with open(g_specDictFile, 'w') as f:
         json.dump(specs, f)

def calcZeta1():
    """
    Counts for each occupation the MSAs where the occupation is specialiced
    """

    MSAs = readJSON(g_specFile)
    zetas = {};
    zaehler = 0
    for msa in MSAs:
        for value in msa["values"]:
            if value["local_quot"]>=1:
                occ = zetas.get(value["code"],{})
                occ["ges"]=occ.get("ges",0)+1
                zetas[value["code"]] = occ
        zaehler = zaehler+1
        print(zaehler,"von",len(MSAs))
    with open('zetas.json', 'w') as f:
         json.dump(zetas, f)

def calcZeta2():
    """
    Counts for each pair of occupations the MSAs where the occupations are specialiced together
    """

    MSAs = readJSON('msaSpecDict.json')
    zetas = readJSON("zetas.json")
    zetasCopy = zetas.copy()
    zaehler = 0
    for occ in zetas.keys():
        for msa in MSAs.keys():
            if MSAs[msa]["values"][occ]>=1:
                for occ2 in zetasCopy.keys():
                    if occ != occ2 and MSAs[msa]["values"][occ2]>=1:
                        zetas[occ][occ2]=zetas[occ].get(occ2,0)+1
                        zetas[occ2][occ]=zetas[occ2].get(occ,0)+1
        del zetasCopy[occ]
        zaehler = zaehler +1
        print(zaehler,"von",len(zetas))
    with open('zetas.json', 'w') as f:
         json.dump(zetas, f)

def calcZeta3():
    """
    Calcutaes for each pair of occupation the propability, that these two occupations are specialiced together
    """

    zetas = readJSON("zetas.json")
    zaehler = 0
    for occ in zetas.keys():
        zetas[occ]["ges"]=zetas[occ]["ges"]/len(zetas)
        for occ2 in zetas.keys():
            if occ == occ2:
                zetas[occ][occ2] = {"prob":zetas[occ]["ges"]}
            else:
                zetas[occ][occ2]= {"prob":zetas[occ][occ2]/len(zetas)}
        zaehler = zaehler +1
        print(zaehler,"von",len(zetas))
    with open('zetas.json', 'w') as f:
         json.dump(zetas, f)
def calcZeta4():
    """
    Calcutaes for each pair of occupation the zeta value based on calculations before
    """

    zetas = readJSON("zetas.json")
    zaehler = 0
    for occ in zetas.keys():
        for occ2 in zetas.keys():
            zetas[occ][occ2]["zeta"]=zetas[occ][occ2]["prob"]/(zetas[occ]["ges"]*zetas[occ2]["ges"])-1
        zaehler = zaehler +1
        print(zaehler,"von",len(zetas))
    with open('zetas.json', 'w') as f:
         json.dump(zetas, f)
def calcZeta():
    """
    Whole set of calculations for the zeta-values
    """

    calcZeta1()
    calcZeta2()
    calcZeta3()
    calcZeta4()

def getTotalEmpsOccNEM(year,parent_path):
    #Get an spec dict with total employees for all occupations from BLS_NEM
    connection = connect("bls_complete")
    cursor = connection.cursor()

    cursor.execute("SELECT Occ_code,base FROM BLS_NEM WHERE Ind_code='TE1000' AND NEM_YEAR ="+str(year))
    result = cursor.fetchall()

    total_emp_spec = {}
    for r in result:
        total_emp_spec[r[0]]=r[1]
    return total_emp_spec

def getTotalEmpsIndNEM(year,parent_path):
    #Get an spec dict with total employees for all occupations from BLS_NEM
    connection = connect("bls_complete")
    cursor = connection.cursor()

    cursor.execute("SELECT Ind_code,base FROM BLS_NEM WHERE Occ_code='00-0000' AND NEM_YEAR ="+str(year))
    result = cursor.fetchall()

    total_emp_spec = {}
    for r in result:
        total_emp_spec[r[0]]=r[1]
    return total_emp_spec

def INDspecialiced(indCode,OCCs,year,total_occ_spec,total_ind_spec,parent_path):
    connection = connect("bls_complete")
    cursor = connection.cursor()

    cursor.execute("SELECT Occ_code,base FROM BLS_NEM WHERE Ind_code='"+indCode+"' AND NEM_YEAR ="+str(year))
    result = cursor.fetchall()
    #MSAs = readJSON(parent_path+'msas.json')
    spec = {}
    for occ in OCCs:
        occData = -1
        for r in result:
            if occ["code"] == r[0]:
                if r[1]:
                    occData = r[1]
                else:
                    occData = 0
                break
        if occData == -1:
            occData = 0
        spec[occ["code"]] = specialiced(150539900,total_occ_spec.get(occ["code"],0),total_ind_spec.get(indCode,0),occData)
        #print(150539900,total_occ_spec.get(occ["code"],0),total_ind_spec.get(indCode,0),occData,specialiced(150539900,total_occ_spec.get(occ["code"],0),total_ind_spec.get(indCode,0),occData))

    connection.close()
    return spec

def testIndSpec(code,OCCs,year,path):
    total_spec_ind = getTotalEmpsIndNEM(year,path)
    total_spec_occ = getTotalEmpsOccNEM(year,path)
    return INDspecialiced(code,OCCs,year,total_spec_occ,total_spec_ind,path)

def restructIndSpec(spec):
    reSpec = [];
    for s in spec.keys():
        reSpec = reSpec + [{"code": s, "local_quot": spec[s]}]
    return reSpec

def calcIndSpec(year):
    path = "mysite/static/"
    OCCs = readJSON(g_occFile)
    total_spec_ind = getTotalEmpsIndNEM(year,path)
    total_spec_occ = getTotalEmpsOccNEM(year,path)

    connection = connect("bls_complete")
    cursor = connection.cursor()
    cursor.execute("SELECT DISTINCT Ind_code FROM BLS_NEM WHERE Ind_type =0 AND NEM_YEAR = "+str(year))
    result = cursor.fetchall()
    specs = readJSON(g_industryFile)
    h = 0
    from runtime_calc import calcGreen
    for r in result:
        new = specs.get(r[0],{"sust_index":-1})["sust_index"]<0
        if new:
            specs[r[0]] = {"sust_index": calcGreen(INDspecialiced(r[0],OCCs,year,total_spec_occ,total_spec_ind,path),"static/")}
        print(h,"von",len(result),"mit",r[0],"=",specs[r[0]]["sust_index"])
        h = h +1
        if h%10 == 1 and new:
            print("Save!")
            with open(g_industryFile, 'w') as f:
                json.dump(specs, f)
    with open(g_industryFile, 'w') as f:
         json.dump(specs, f)

def readTotalEmpOcc(von,bis):
    """
    Reads the count of total employes from the database for each occuaption
    INPUT: von (int), bis(int). For a negative bis-value, all occupations are included
    """
    data_loaded = readJSON(g_occFile)
    connection = connect("bls_complete")
    cursor = connection.cursor()
    counter = 0
    if bis < 0:
        bis = len(data_loaded)
    for i in range(von,bis):
        data_loaded[i]["total_emp"] = {}
        cursor.execute("SELECT TOT_EMP,OES_YEAR FROM BLS_OES WHERE AREA='00000' AND OCC_CODE='"+data_loaded[i]["code"]+"' ")
        result = cursor.fetchall()
        for r in result:
            data_loaded[i]["total_emp"][r[1]] = r[0]
        counter = counter +1
        print(str(counter) + " von "+str(bis-von))
    with open(g_occFile, 'w') as f:
         json.dump(data_loaded, f)
    connection.close()

