import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Depends, FastAPI, HTTPException, status, Request, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from pydantic import BaseModel
import psycopg2 as psycopg
import time
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_USER = os.getenv('DATABASE_USER')
DATABASE_NAME=os.getenv('DATABASE_NAME')
DATABASE_HOST=os.getenv('DATABASE_HOST')
DATABASE_PORT=os.getenv('DATABASE_PORT')
DATABASE_PASSWORD=os.getenv('DATABASE_PASSWORD')

app = FastAPI()
defaultread = {
    "read_id":0,
    "read_time":0,
    "ph":0,
    "turbidity" : 0
}
class Reading (BaseModel):
    read_id : int
    read_date : datetime
    ph : float
    turbidity : float
    temp : float
    dissoxy : float
    orp : float
    conductivity : float
    class Config:
        orm_mode = True

origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://shrouded-retreat-23800.herokuapp.com",
    "https://shrouded-retreat-23800.herokuapp.com",
    "https://localhost:1234",
    "http://localhost:1234/",
    "http://localhost:1234",
    "https://waterlity.herokuapp.com",
    "http://waterlity.herokuapp.com",
    "http://waterlity.herokuapp.com/",
    "https://nthnlius.github.io/Reksti-Waterlity/"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
def normdist(mean, stddev):
    bwh05 = mean-(stddev/2)
    bwh1 = mean-stddev
    bwh2 = mean - (2*stddev)
    bwh3 = mean - (3*stddev)
    bwh = [bwh05, bwh1, bwh2, bwh3]
    ats05 = mean+(stddev/2)
    ats1 = mean+stddev
    ats2 = mean+(2*stddev)
    ats3 = mean+(3*stddev)
    ats = [ats05, ats1, ats2, ats3]
    return bwh, ats
def compare(read : list):
    ba=[]
    bb=[]
    db= psycopg.connect(dbname = DATABASE_NAME, user=DATABASE_USER, password = DATABASE_PASSWORD, port = DATABASE_PORT, host = DATABASE_HOST)
    query= db.cursor()
    query.execute("SELECT AVG(ph), AVG(turbidity), AVG(dissoxy), AVG(temp), AVG(orp), AVG(conductivity) FROM read_valid;")
    avg = query.fetchone()
    query.execute("SELECT STDDEV(ph), STDDEV(turbidity), STDDEV(dissoxy), STDDEV(temp), STDDEV(orp), STDDEV(conductivity) from read_valid;")
    stddev=query.fetchone()
    for i in range (len(avg)):
        a,b = normdist(avg[i], stddev[i])
        ba.append(a)
        bb.append(b)
    nilai=0
    test = 1
    for i in range (len(read)):
        if (read[i]>ba[i][3]) or (read[i]<bb[i][3]):
            nilai = 0
            test= test*0
            break
        elif (read[i]> ba[i][2]) or (read[i]<bb[i][2]):
            nilai +=1
            test = test*0.5
        elif (read[i]>ba[i][1] and read[i]<bb[i][1]):
            nilai +=2
            test = test*0.8
        else:
            nilai +=3
            test = test*1.1
    return nilai, test
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
@app.post('/read', tags = ['Add reading'])
def write_from_sensor (read : Reading = Body(default = "", embed=True)):
    db= psycopg.connect(dbname = DATABASE_NAME, user=DATABASE_USER, password = DATABASE_PASSWORD, port = DATABASE_PORT, host = DATABASE_HOST)
    query= db.cursor()
    pH = read.ph
    temp = read.temp
    turbid = read.turbidity
    dissoxy = read.dissoxy
    orp = read.orp 

    cond = read.conductivity
    read = [pH, temp, turbid, dissoxy, orp, cond]
    nilai = compare(read)
    if (nilai > 12):
        query.execute("INSERT INTO read_valid(read_time, ph, temp, turbidity, dissoxy, orp, conductivity) VALUES(%s, %s, %s, %s, %s, %s, %s)", ("NOW()", pH, temp, turbid, dissoxy, orp, cond))
        db.commit()
        query.execute("INSERT INTO allread(read_time, ph, temp, turbidity, dissoxy, orp, conductivity) VALUES(%s, %s, %s, %s, %s, %s, %s)", ("NOW()", pH, temp, turbid, dissoxy, orp, cond))
        db.commit()
        # query.execute("SELECT * from allread;")
        # exist = query.fetchone()
        query.close()
        db.close()
        return "success"
    else :
        query.execute("INSERT INTO allread(read_time, ph, temp, turbidity, dissoxy, orp, conductivity) VALUES(%s, %s, %s, %s, %s, %s, %s)", ("NOW()", pH, temp, turbid, dissoxy, orp, cond))
        db.commit()
        # query.execute("SELECT * from allread;")
        # exist = query.fetchone()
        query.close()
        db.close()
        return "water quality unqualified"
    # query.execute("INSERT INTO read_sensor(read_time, ph, temp, turbidity, dissoxy, orp, conductivity) VALUES(%s, %s, %s, %s, %s, %s, %s)", ("NOW()", pH, temp, turbid, dissoxy, orp, cond))
    # db.commit()
    # # query.execute("SELECT * from allread;")
    # # exist = query.fetchone()
    # query.close()
    # db.close()
    # return "success"
@app.get('/Averages', tags=['Counting Aggregate'])
def count_averages():
    # db = psycopg.connect(dbname = "vrhknqtr", user="vrhknqtr", password = "ca84d1343b96baa8137c943ed1860e522cacb238", port = 5432, host="waterlity.csdxgsce0fbt.ap-southeast-1.rds.amazonaws.com")
    db= psycopg.connect(dbname = DATABASE_NAME, user=DATABASE_USER, password = DATABASE_PASSWORD, port = DATABASE_PORT, host = DATABASE_HOST)
    query = db.cursor()
    query.execute("SELECT AVG(ph), AVG(turbidity), AVG(dissoxy), AVG(temp), AVG(orp), AVG(conductivity) from allread;")
    reading = query.fetchone()
    avgph=reading[0]
    avgturb = reading[1]
    avgdissoxy = reading[2]
    avgtemp = reading[3]
    avgorp = reading[4]
    avgcond = reading[5]
    # print ()
    return {"avgph":avgph, "avgturbidity":avgturb, "avgdissox":avgdissoxy, "avgtemp":avgtemp, "avgoxired":avgorp, "avgconductivity":avgcond}
@app.get('/Minimum', tags=["Counting Aggregate"])
def count_minimum():
    db= psycopg.connect(dbname = DATABASE_NAME, user=DATABASE_USER, password = DATABASE_PASSWORD, port = DATABASE_PORT, host = DATABASE_HOST)
    query = db.cursor()
    query.execute("SELECT MIN(ph), MIN(turbidity), MIN(dissoxy), MIN(temp), MIN(orp), MIN(conductivity) from allread;")
    reading = query.fetchone()
    minph = reading[0]
    minturb = reading[1]
    mindissoxy=reading[2]
    mintemp = reading[3]
    minorp = reading[4]
    mincond = reading[5]
    return {"minph":minph, "minturbidity":minturb,"mindissox":mindissoxy, "mintemp":mintemp, "minoxired":minorp, "minconductivity":mincond}

@app.get('/Maximum', tags=["Counting Aggregate"])
def count_maximum():
    db= psycopg.connect(dbname = DATABASE_NAME, user=DATABASE_USER, password = DATABASE_PASSWORD, port = DATABASE_PORT, host = DATABASE_HOST)
    query = db.cursor()
    query.execute("SELECT Max(ph), Max(turbidity), Max(dissoxy), Max(temp), Max(orp), Max(conductivity) from allread;")
    reading = query.fetchone()
    minph = reading[0]
    minturb = reading[1]
    mindissoxy=reading[2]
    mintemp = reading[3]
    minorp = reading[4]
    mincond = reading[5]
    return {"maxph":minph, "maxturbidity":minturb,"maxdissox":mindissoxy, "maxtemp":mintemp, "maxoxired":minorp, "maxconductivity":mincond}
    
@app.get('/Kelayakan-minum-secara-smart', tags=["Kelayakan minum secara smart"])
def Kelayakan_last_reading():
    db= psycopg.connect(dbname = DATABASE_NAME, user=DATABASE_USER, password = DATABASE_PASSWORD, port = DATABASE_PORT, host = DATABASE_HOST)
    query = db.cursor()
    query.execute("SELECT AVG(ph), AVG(turbidity), AVG(dissoxy), AVG(temp), AVG(orp), AVG(conductivity) from allread;")
    avg= query.fetchone()
    avgph=avg[0]
    avgturb = avg[1]
    avgdissoxy = avg[2]
    avgtemp = avg[3]
    query.execute("Select ph, turbidity, dissoxy, temp from allread order by read_time desc;")
    lastreading = query.fetchone()
    lastph = lastreading[0]
    lastturb = lastreading[1]
    lastdissoxy = lastreading[2]
    lasttemp = lastreading[3]
    ksrph = 1-(abs(lastph-avgph)/avgph)
    ksrturb = 1-(abs(lastturb-avgturb)/avgturb)
    ksrdissoxy = 1-(abs(lastdissoxy-avgdissoxy)/avgdissoxy)
    ksrtemp = 1-(abs(lasttemp-avgtemp)/avgtemp)
    appropriateness = abs(ksrph * ksrdissoxy * ksrtemp * ksrturb)
    return {"Kelayakan minum" : appropriateness}
@app.get('/Kelayakan-minum-secara-smart2', tags=["Kelayakan minum secara smart"])
def Kelayakan2():
    db= psycopg.connect(dbname = DATABASE_NAME, user=DATABASE_USER, password = DATABASE_PASSWORD, port = DATABASE_PORT, host = DATABASE_HOST)
    query = db.cursor()
    query.execute("Select ph, turbidity, dissoxy, temp from allread order by read_time desc;")
    lastread = query.fetchone()
    nilai, result = compare(lastread)
    return {'Kelayakan minum' : {nilai, result}}
@app.get('/Kelayakan-minum', tags=["Kelayakan minum secara normal"])
def Kelayakan_minum():
    db= psycopg.connect(dbname = DATABASE_NAME, user=DATABASE_USER, password = DATABASE_PASSWORD, port = DATABASE_PORT, host = DATABASE_HOST)
    query = db.cursor()
    query.execute("Select ph, turbidity, dissoxy, temp, orp, conductivity from allread order by read_time desc;")
    lastreading = query.fetchone()
    lastph = lastreading[0]
    lastturb = lastreading[1]
    lastdissoxy = lastreading[2]
    lasttemp = lastreading[3]
    if lastdissoxy > 4 :
        if lastturb < 0.5 :
            if lasttemp>=24 and lasttemp <=30 :
                if lastph >= 6.5 and lastph <=8.5:
                    return {"Kelayakan" : "layak"}
    return {"Kelayakan" : "Tidak layak"}

@app.get('/Kelayakan-sanitasi', tags=["Kelayakan sanitasi"])
def Kelayakan_sanitasi():
    db= psycopg.connect(dbname = DATABASE_NAME, user=DATABASE_USER, password = DATABASE_PASSWORD, port = DATABASE_PORT, host = DATABASE_HOST)
    query = db.cursor()
    query.execute("Select ph, turbidity, dissoxy, temp, orp, conductivity from allread order by read_time desc;")
    lastreading = query.fetchone()
    lastph = lastreading[0]
    lastturb = lastreading[1]
    lastdissoxy = lastreading[2]
    lasttemp = lastreading[3]
    if lastturb < 0.5 :
        if lasttemp>=16 and lasttemp <=30 :
            if lastph >= 6.5 and lastph <=8.5:
                return {"Kelayakan" : "layak"}
    return {"Kelayakan" : "Tidak layak"}
@app.get('/Kelayakan-mandi', tags=["Kelayakan mandi"])
def Kelayakan_mandi():
    db= psycopg.connect(dbname = DATABASE_NAME, user=DATABASE_USER, password = DATABASE_PASSWORD, port = DATABASE_PORT, host = DATABASE_HOST)
    query = db.cursor()
    query.execute("Select ph, turbidity, dissoxy, temp, orp, conductivity from allread order by read_time desc;")
    lastreading = query.fetchone()
    lastph = lastreading[0]
    lastturb = lastreading[1]
    lastdissoxy = lastreading[2]
    lasttemp = lastreading[3]
    if lastdissoxy >= 4:
        if lastturb < 0.5 :
            if lasttemp>=16 and lasttemp <=30 :
                if lastph >= 6.5 and lastph <=8.5:
                    return {"Kelayakan" : "layak"}
    return {"Kelayakan" : "Tidak layak"}

@app.get('/Kelayakan-tani', tags=["Kelayakan tani"])
def Kelayakan_sanitasi():
    db= psycopg.connect(dbname = DATABASE_NAME, user=DATABASE_USER, password = DATABASE_PASSWORD, port = DATABASE_PORT, host = DATABASE_HOST)
    query = db.cursor()
    query.execute("Select ph, turbidity, dissoxy, temp, orp, conductivity from allread order by read_time desc;")
    lastreading = query.fetchone()
    lastph = lastreading[0]
    lastturb = lastreading[1]
    lastdissoxy = lastreading[2]
    lasttemp = lastreading[3]
    lastorp = lastreading[4]
    lastcond = lastreading[5]
    if lastdissoxy >= 0:
        if lastturb < 30 and lastturb > 0.2 :
            if lasttemp>=29 and lasttemp <=33 :
                if lastph >= 5 and lastph <=9:
                    if lastcond < 250 :
                        if lastorp >=300 and lastorp<=500 :
                            return {"Kelayakan" : "layak"}
    return {"Kelayakan" : "Tidak layak"}

@app.get('/Kelayakan-perikanan', tags=["Kelayakan perikanan"])
def Kelayakan_sanitasi():
    db= psycopg.connect(dbname = DATABASE_NAME, user=DATABASE_USER, password = DATABASE_PASSWORD, port = DATABASE_PORT, host = DATABASE_HOST)
    query = db.cursor()
    query.execute("Select ph, turbidity, dissoxy, temp, orp, conductivity from allread order by read_time desc;")
    lastreading = query.fetchone()
    lastph = lastreading[0]
    lastturb = lastreading[1]
    lastdissoxy = lastreading[2]
    lasttemp = lastreading[3]
    lastorp = lastreading[4]
    lastcond = lastreading[5]
    if lastdissoxy > 4:
        if lastturb < 30 and lastturb > 0.2 :
            if lasttemp>=28 and lasttemp <=32 :
                if lastph >= 6 and lastph <=9:
                    if lastcond < 250 :
                        if lastorp >=300 and lastorp<=500 :
                            return {"Kelayakan" : "layak"}
    return {"Kelayakan" : "Tidak layak"}

@app.get('/last-read', tags=["Pembacaan nilai terakhir"])
def last_read():
    db= psycopg.connect(dbname = DATABASE_NAME, user=DATABASE_USER, password = DATABASE_PASSWORD, port = DATABASE_PORT, host = DATABASE_HOST)
    query = db.cursor()
    query.execute("Select ph, turbidity, dissoxy, temp, orp, conductivity from allread order by read_time desc;")
    lastreading = query.fetchone()
    lastph = lastreading[0]
    lastturb = lastreading[1]
    lastdissoxy = lastreading[2]
    lasttemp = lastreading[3]
    lastorp = lastreading[4]
    lastcond = lastreading[5]
    return {"lastph" : lastph, "lastturb" : lastturb, "lastdissoxy" : lastdissoxy, "lasttemp" : lasttemp, "lastorp":lastorp, "lastcond":lastcond}