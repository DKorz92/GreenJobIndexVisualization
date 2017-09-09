#!/usr/bin/python3.5
# A very simple Bottle Hello World app for you to get started with...
from bottle import default_app, route, request, debug, static_file, response
import MySQLdb
import runtime_calc
import jsonutils
import json
from dbConnector import connect

g_parentPath = "mysite/DecisionHelper/HTML/"
#g_staticPath = "../static/"
g_staticPath = "mysite/DecisionHelper/static/"
g_year = 2015;

@route("/getQuestionaire")
def getQuestionaire():
    questionaire = [{"NAME":"Test1", "QUESTIONS":[{"INDEX":"TEST"}]}]

@route("/getMSAData")
def getMSAData():
    MSAs = jsonutils.readJSON(g_staticPath + 'msas.json')
    MSAs = sorted(MSAs,key=getRankValue)
    MSAback = []
    for m in MSAs:
        green = 0
        ranked = 0
        if m.get("overYear",[]) == []:
            continue
        for y in m["overYear"]:
            if y["year"]==g_year:
                green = y["value"]
                ranked = y["rank"]
                break
        MSAback = MSAback + [{"name":m["name"],"code": m["code"],"greenIndex":green,"ranked":ranked}]
    return json.dumps({"year":g_year,"values":MSAback})

def getRankValue(d):
    for y in d.get("overYear",[]):
        if y["year"]==g_year:
            return y["rank"]
    return 0
@route("/checkMSA/<msaCode>/<layerJSON>")
def checkMSA(msaCode,layerJSON):
    OCCs = jsonutils.readJSON(g_staticPath+'ocspacepoints.json')
    attractOccByInd(OCCs,layerJSON)
    MSAs = jsonutils.readJSON(g_staticPath+'msaSpec.json')
    msa = []
    for msaSearch in MSAs:
        if msaSearch["code"] == msaCode:
            msa = msaSearch
            break
    msa["values"]=runtime_calc.MSAspecialiced(msa["code"],OCCs,"2015",g_staticPath)
    return json.dumps(msa)
    #Testcase: checkMSA("14260",'{"name":"Layer for Boise City, ID","layers":[],"inds":[{"code":"221100","reward":15950},{"code":"325100","reward":0}]}')

@route("/newlyMSA/<layerJSON>")
def newlyMSA(layerJSON):
    msaCode = json.loads(layerJSON)["msa"]["code"]
    msa = json.loads(checkMSA(str(msaCode),"{}"))
    msaNew = json.loads(checkMSA(str(msaCode),layerJSON))
    newOnes = []
    for m in msa["values"]:
        if m["green_flag"] == 0 or m["local_quot"] >=1:
            continue
        for mNew in msaNew["values"]:
            if mNew["code"] == m["code"]:
                if mNew["local_quot"]>= 1:
                    newOnes = newOnes + [mNew]
                break
    return json.dumps(newOnes)
    #Testcase newlyMSA('{"name":"Layer for Phoenix-Mesa-Scottsdale, AZ","msa":{"name":"Phoenix-Mesa-Scottsdale, AZ","code":38060},"occs":[],"inds":[{"name":"Electric power generation, transmison and distribution","code":"221100","reward":555}],"base":false,"layers":[]}')

def attractOccByInd(OCCs,layerJSON):
    layer = json.loads(layerJSON)
    #for l in layer:
    for i in layer.get("inds",[]):
        runtime_calc.industryReward(i["code"],i["reward"],OCCs)

@route("/msaOverTime/<msaCode>/<layerJSON>")
def msaOverTime(msaCode,layerJSON):
    MSAs = jsonutils.readJSON(g_staticPath + 'msas.json')
    selectedMSA = {}
    for msa in MSAs:
        if msa["code"]==msaCode:
            selectedMSA = msa
            break
    back = []
    if not selectedMSA.get("overYear",-1)== -1:
        back = selectedMSA["overYear"]
    else:
        OCCs = jsonutils.readJSON(g_staticPath+'ocspacepoints.json')
        connection = connect("bls_complete")
        cursor = connection.cursor()
        cursor.execute("SELECT DISTINCT OES_YEAR FROM BLS_OES WHERE AREA = '"+msaCode+"'")
        result = cursor.fetchall()
        for r in result:
            back = back + [{"year": r[0],"value": runtime_calc.calcGreen(runtime_calc.MSAspecialiced(msaCode,OCCs,r[0],g_staticPath),g_staticPath)}]
            print(r[0],"fertig")
        connection.close()
        selectedMSA["overYear"] = back
        with open(g_staticPath + 'msas.json', 'w') as f:
            json.dump(MSAs, f)
    if(layerJSON!="{}"):
        OCCs = jsonutils.readJSON(g_staticPath+'ocspacepoints.json')
        attractOccByInd(OCCs,layerJSON)
        yearMax = 0
        for b in back:
            if b["year"]>yearMax:
                yearMax = b["year"]
        value = runtime_calc.calcGreen(runtime_calc.MSAspecialiced(msaCode,OCCs,yearMax,g_staticPath),g_staticPath)
        rank = jsonutils.calcRank(value,yearMax)
        back = back + [{"year": (-1)*yearMax,"value": value,"rank":rank}]
    return json.dumps({"code":msaCode,"values":back});
@route("/checkOCs/<msaCode>/<layerJSON>")
def checkOCs(msaCode,layerJSON):
    layer = json.loads(layerJSON)
    OCCs = jsonutils.readJSON(g_staticPath+'ocspacepoints.json')
    MSAs = jsonutils.readJSON(g_staticPath+'msaSpecDict.json')
    attractOccByInd(OCCs,layerJSON)
    OCCs = runtime_calc.calcTrans(MSAs[msaCode],OCCs,g_staticPath)
    connection = connect("bls_complete")
    cursor = connection.cursor()
    query_old = ''' SELECT b1.OCC_CODE,b2.H_MEAN,b2.A_MEAN,b2.H_MEDIAN,b2.A_MEDIAN,b1.H_MEAN,b1.A_MEAN,b1.H_MEDIAN,b1.A_MEDIAN,b2.OES_YEAR
                FROM BLS_OES b1, BLS_OES b2
                WHERE b1.AREA = "00000" AND b2.AREA = "'''+msaCode+'''"  AND b1.OCC_CODE = b2.OCC_CODE AND b1.OES_YEAR = b2.OES_YEAR AND b1.OES_YEAR =
                    (SELECT MAX(b1.OES_YEAR)
                    FROM BLS_OES b1, BLS_OES b2
                    WHERE b1.AREA = "00000" AND b2.AREA = "'''+msaCode+'''"  AND b1.OCC_CODE = b2.OCC_CODE AND b1.OES_YEAR = b2.OES_YEAR)
                ORDER BY b2.OCC_CODE,b2.OES_YEAR DESC;''';
    query_USA = ''' SELECT b1.OCC_CODE,b1.H_MEAN,b1.A_MEAN,b1.H_MEDIAN,b1.A_MEDIAN,b1.OES_YEAR
                FROM BLS_OES b1
                WHERE b1.AREA = "00000"
                ORDER BY b1.OES_YEAR DESC;''';
    query_MSA = ''' SELECT b1.OCC_CODE,b1.H_MEAN,b1.A_MEAN,b1.H_MEDIAN,b1.A_MEDIAN,b1.OES_YEAR
                FROM BLS_OES b1
                WHERE b1.AREA = "'''+msaCode+'''"
                ORDER BY b1.OES_YEAR DESC;''';
    cursor.execute(query_USA)
    result_USA = cursor.fetchall()
    cursor.execute(query_MSA)
    result_MSA = cursor.fetchall()
    connection.close()
    for o in OCCs:
        o["h_mean"]=[-1,-1,-1]
        o["a_mean"]=[-1,-1,-1]
        o["h_median"]=[-1,-1,-1]
        o["a_median"]=[-1,-1,-1]
        for r in result_USA:
            if r[0] == o["code"]:
                if r[1]:
                    o["h_mean"][1]=float(r[1])
                if r[2]:
                    o["a_mean"][1]=float(r[2])
                if r[3]:
                    o["h_median"][1]=float(r[3])
                if r[4]:
                    o["a_median"][1]=float(r[4])
                o["usa_year"] = r[5]
                break
        for r in result_MSA:
            if r[0] == o["code"]:
                if r[1]:
                    o["h_mean"][0]=float(r[1])
                if r[2]:
                    o["a_mean"][0]=float(r[2])
                if r[3]:
                    o["h_median"][0]=float(r[3])
                if r[4]:
                    o["a_median"][0]=float(r[4])
                o["msa_year"] = r[5]
                break
        if not o["h_mean"][0] == -1 and not o["h_mean"][1] == -1:
            o["h_mean"][2]=o["h_mean"][0]/o["h_mean"][1]*100
        if not o["a_mean"][0] == -1 and not o["a_mean"][1] == -1:
            o["a_mean"][2]=o["a_mean"][0]/o["a_mean"][1]*100
        if not o["h_median"][0] == -1 and not o["h_median"][1] == -1:
            o["h_median"][2]=o["h_median"][0]/o["h_median"][1]*100
        if not o["a_median"][0] == -1 and not o["a_median"][1] == -1:
            o["a_median"][2]=o["a_median"][0]/o["a_median"][1]*100


    return json.dumps(OCCs)

@route("/getIndustries/<msaCode>/<occs>")
def getPossibleIndustries(msaCode,occs):
    OCCs = json.loads(occs)
    connection = connect("bls_complete")
    cursor = connection.cursor()
    query = '''SELECT bls_nem_industries.`Industry title`, bls_nem_industries.`Industry code` , BLS_NEM.Occ_code, BLS_NEM.pc_occ_base, BLS_NEM.pc_occ_proj , bls_nem_industries.`Industry type`
    FROM BLS_NEM, bls_nem_industries
    WHERE BLS_NEM.Ind_code = bls_nem_industries.`industry code` AND BLS_NEM.NEM_year = bls_nem_industries.NEM_Year AND BLS_NEM.Ind_Type = 0 AND bls_nem_industries.NEM_Year = 2014
    AND (FALSE '''

    for occ in OCCs:
        query = query + '''OR BLS_NEM.Occ_code = "''' + occ["code"] + '"'
    query = query + ")"
    cursor.execute(query)
    result = cursor.fetchall()
    spec = []
    OCCs = jsonutils.readJSON(g_staticPath+'ocspacepoints.json')
    INDs = jsonutils.readJSON(g_staticPath+'industries.json')
    msa = runtime_calc.MSAspecialiced(msaCode,OCCs,"2014",g_staticPath)
    from pre_calc import testIndSpec
    from pre_calc import restructIndSpec
    for r in result:
        sust_index = 0
        advanced = False
        if INDs.get(r[1]) and INDs[r[1]].get(msaCode):
            sust_index = INDs[r[1]][msaCode]
            advanced = INDs[r[1]]["advanced_flag"]
        else:
            print(r[1])
            ind = testIndSpec(r[1],OCCs,2014,g_staticPath)
            sust_index = runtime_calc.calcSuitability(msa,ind,g_staticPath)
            if not INDs.get(r[1]):
                INDs[r[1]] = {}
            INDs[r[1]][msaCode] = sust_index;
            with open(g_staticPath + 'industries.json', 'w') as f:
                json.dump(INDs, f)
        if not INDs[r[1]].get("green"):
            ind = restructIndSpec(testIndSpec(r[1],OCCs,2014,g_staticPath))
            INDs[r[1]]["green"]= runtime_calc.calcGreen(ind,g_staticPath)
            with open(g_staticPath + 'industries.json', 'w') as f:
                json.dump(INDs, f)
        spec = spec  + [{"title":r[0], "ind_code": r[1], "occ_code": r[2], "base": r[3], "proj": r[4],"salary":INDs[r[1]]["green"],"sust_index":sust_index,"advanced": advanced}]
    return json.dumps(spec)

@route("/getIndustries/<msaCode>")
def getAllIndustries(msaCode):
    connection = connect("bls_complete")
    cursor = connection.cursor()
    query = '''SELECT DISTINCT bls_nem_industries.`Industry title`, bls_nem_industries.`Industry code` , bls_nem_industries.`Industry type`
    FROM BLS_NEM, bls_nem_industries
    WHERE BLS_NEM.Ind_code = bls_nem_industries.`industry code` AND BLS_NEM.NEM_year = bls_nem_industries.NEM_Year AND BLS_NEM.Ind_Type = 0 AND bls_nem_industries.NEM_Year = 2014'''
    cursor.execute(query)
    result = cursor.fetchall()
    spec = []
    OCCs = jsonutils.readJSON(g_staticPath+'ocspacepoints.json')
    INDs = jsonutils.readJSON(g_staticPath+'industries.json')
    msa = runtime_calc.MSAspecialiced(msaCode,OCCs,"2014",g_staticPath)
    from pre_calc import testIndSpec
    from pre_calc import restructIndSpec
    for r in result:
        sust_index = 0
        if INDs.get(r[1]) and INDs[r[1]].get(msaCode):
            sust_index = INDs[r[1]][msaCode]
        else:
            print(r[1])
            ind = testIndSpec(r[1],OCCs,2014,g_staticPath)
            sust_index = runtime_calc.calcSuitability(msa,ind,g_staticPath)
            if not INDs.get(r[1]):
                INDs[r[1]] = {}
            INDs[r[1]][msaCode] = sust_index;
            with open(g_staticPath + 'industries.json', 'w') as f:
                json.dump(INDs, f)
        if not INDs[r[1]].get("green"):
            ind = restructIndSpec(testIndSpec(r[1],OCCs,2014,g_staticPath))
            INDs[r[1]]["green"]= runtime_calc.calcGreen(ind,g_staticPath)
            with open(g_staticPath + 'industries.json', 'w') as f:
                json.dump(INDs, f)
        spec = spec  + [{"title":r[0], "ind_code": r[1], "occ_code": "00-000", "base": INDs[r[1]]["green"]*sust_index, "proj": 1,"salary":INDs[r[1]]["green"],"sust_index":sust_index}]
    spec = spec  + [{"title":"Norm_min", "ind_code": "000000", "occ_code": "00-000", "base": 1, "proj": 0,"salary":0,"sust_index":0}]
    spec = spec  + [{"title":"Norm_max", "ind_code": "000000", "occ_code": "00-000", "base": 0, "proj": 0,"salary":1,"sust_index":1}]
    return json.dumps(spec)

def testScript():
    OCCs = jsonutils.readJSON(g_staticPath+'ocspacepoints.json')
    from pre_calc import testIndSpec
    from pre_calc import restructIndSpec
    ind = restructIndSpec(testIndSpec("51-9122",OCCs,2014,g_staticPath))
    print(ind)
    #getPossibleIndustries("14260",'[{"code":"17-2041"}]')

@route("/getEmpSolution/<params>")
def calcSolution(params):
    params = json.loads(params)
    occCodes = params["OCCs"]
    indCodes = params["INDs"]
    msaCode = params["MSA"]["code"]
    missings = []
    for occ in occCodes:
        missings = missings + [runtime_calc.missingEmps(str(msaCode),str(occ["code"]),"2015","mysite/static/")]
    indOccBase = []

    query = '''SELECT  bls_nem_industries.`Industry code` , BLS_NEM.Occ_code, BLS_NEM.pc_occ_base
    FROM BLS_NEM, bls_nem_industries
    WHERE BLS_NEM.Ind_code = bls_nem_industries.`industry code` AND BLS_NEM.NEM_year = bls_nem_industries.NEM_Year AND BLS_NEM.Ind_Type = 0 AND bls_nem_industries.NEM_Year = 2014 AND (FALSE '''

    for occ in occCodes:
        query = query + "OR BLS_NEM.Occ_code = '"+str(occ["code"])+"' "
    query = query + ") AND (FALSE "
    for ind in indCodes:
        query = query + "OR BLS_NEM.Ind_code = '"+str(ind["code"])+"' "
    query = query + ")"
    #print(query)
    connection = connect("bls_complete")
    cursor = connection.cursor()
    cursor.execute(query)
    result = cursor.fetchall()
    connection.close()

    for occ in occCodes:
        indBase = []
        for ind in indCodes:
            found = False
            for r in result:
                if r[0] == str(ind["code"]) and r[1] == str(occ["code"]):
                    indBase = indBase + [r[2]/100]
                    found = True
                    break
            if not found:
                indBase = indBase + [0]
        indOccBase = indOccBase + [indBase]
    print(missings,indOccBase)
    return json.dumps(runtime_calc.calcNeeded(missings,indOccBase))
    #Testcase1: calcSolution('{"MSA":{"code": "14260"},"INDs":[{"code": "336400"},{"code": "334400"}],"OCCs":[{"code": "51-9061"},{"code": "49-9044"}]}')
    #Testcase2: calcSolution('{"MSA":{"code":14260},"OCCs":[{"code":"47-2231"},{"code":"49-9081"}],"INDs":[{"code":"237130"}]}')

    #return result

@route("/test")
def test():
    OCCs = jsonutils.readJSON('mysite/static/msas.json')
    return json.dumps(OCCs)

def readHTML(path):
    t = ""
    for line in open(g_parentPath+path+".html"):
        t = t+line
    return t

def getHTML(htmlPart,backstep=False):
    html = '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">'
    html = html + readHTML("header")
    html = html + readHTML("style")
    html = html +"<body>"
    html = html + readHTML("introduction")
    #html = html +"<p>Welcome to this site! You can read <a href = '/docu'> here </a> an introdution</p>"
    html = html +'''<div id='loadingPage'>
                        <h2>Please wait a moment, the page is still loading.</h2>
                    </div>'''
    html = html + '''<div id='toolDiv' style='visibility:hidden;'>
                        <h1>Take a look on the Green Jobs Index</h1>
                        <div class="textDiv">
                            <p>Every panel gives you different information which could be interesting in exploring the way to become a green economy. </p>
                            <p>You can change the main panel with double click on the panel of your interest.</p>
                        </div>
                        <div id='visualization' >
                            <h2 id='panelHeader'></h2>
                            <p id='helpIcon' class='helpIcon'>?<title>Need more information?</title></p>'''
    html = html +readHTML("globals")
    html = html +readHTML("map")
    html = html +readHTML("MSAPanel")
    html = html +readHTML("msaOverTimePanel")
    html = html +readHTML("occupationGraphPanel")
    #html = html + "<div class='panelSide'></div>"
    #html = html + "<div class='panelSide'></div>"
    #html = html + "<div class='panelSide'></div>"
    html = html +readHTML("occupationSpacePanel")
    html = html +readHTML("industryPanel")
    html = html +readHTML("layerPanel")
    html = html + readHTML("framework")
    html = html +'''<script>g_dataState.p_layout=sideBarLayout;setTimeout('g_refreshAll()', 1500);setTimeout("d3.select('#loadingPage').remove();d3.select('#toolDiv').style('visibility','visible')",3000)</script>'''
    html = html +readHTML("staticMSASelection")
    html = html +"<div id='panelDescription' class='textDiv' style='visibility: visible;'></div></div></div>"
    html = html +"<div><p>Created in Cooperation with TU Kaiserslautern and Arizona State University</div>"
    html = html +"</body></html>"
    return html
@route('/database',method="GET")
def inputdb():
    html = '''<form action='/database' method='POST'>
        <div>
            <table>
                <tr><td>Code:</td><td><input type='text' name='code'></td></tr>
            </table>
            <button type='submit' value='submit'>Absenden</button>
        </div>
    </form>'''
    return getHTML(html)
@route('/database',method="POST")
def printdb():
    code = request.forms.get('code')
    connection = connect("bls_complete")
    cursor=connection.cursor()
    try:
        cursor.execute(code)
        result = cursor.fetchall()
        html = "<div><table>"
        for res in result:
            html = html + "<tr>"
            for r in res:
                html = html + "<td>"+str(r)+"</td>"
            html = html + "</tr>"
        html = html + "</table><a href='/database'>Neue Eingabe</a></div>"
        connection.commit()
        connection.close()
        return getHTML(html)
    except MySQLdb.Error as err:
        connection.close()
        return getHTML("<h2>Eingabe fehlgeschlagen</h2>"+str(err)+"<a href='/database'>Neue Eingabe</a>")

@route('/')
def start():
    return getHTML("Test")
@route('/docu')
def documentation():
    html = '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">'
    html = html + readHTML("header")
    html = html + readHTML("style")
    html = html + "<body>"+readHTML("documentation")+"</body>"
    html = html + '</html>'
    return html


application = default_app()
debug(True)

