#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
#===========================================================================================================
Copyright (c) 2020 Paseman & Associates

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
#===========================================================================================================
Version 0: End to End Python Code to get Flume data and display it in linear/log format over a variable timeframe.

https://tools.ietf.org/html/rfc6750
https://flumetech.readme.io/reference#fetch-all-event-rules-for-a-device
https://flumetech.readme.io/reference#accessing-the-api

JWT Hint
  import jwt
  # https://codepunk.io/decoding-json-web-tokens-jwt-in-python-flask-applications/
  # url = "https://api.flumewater.com/users/user_id"
  try:
    decoded = jwt.decode(request.cookies['my.site.jwt'], '<MY SECRET KEY>', algorithms=['HS256'])
    if 'sub' in decoded:
      user_id = decoded['sub']
  except:
    print('Decoding jwt failed.')

"""

# https://stackoverflow.com/questions/39780403/python3-read-json-file-from-url
# data = json.loads(requests.get(url).text)
import json
import requests
import pandas as pd
import plotly.express as px

# DOES NOT WORK UNLESS YOU FILL IN THE FOUR VARIABLES BELOW FROM
# From https://portal.flumewater.com/settings
CLIENTID = ""
CLIENTSECRET = ""
USERNAME = ""
PASSWORD = ""

#===========================================================================================================
# https://flumetech.readme.io/reference#get-tokens-1
def flumeTokens(client_id=CLIENTID,client_secret=CLIENTSECRET,username=USERNAME,password=PASSWORD):
  url = "https://api.flumewater.com/oauth/token"
  payload = "{\"grant_type\":\"password\",\"client_id\":\"%s\",\"client_secret\":\"%s\",\"username\":\"%s\",\"password\":\"%s\"}"%\
            (client_id,client_secret,username,password)
  headers = {'content-type': 'application/json'}
  response = requests.request("POST", url, data=payload, headers=headers)
  # 604800/(3600*24) = 7 days
  r = json.loads(response.text)
  return r['data'][0]['access_token'],r['data'][0]['refresh_token']

#===========================================================================================================
# https://flumetech.readme.io/reference#refresh-access-token-1
def flumeRefreshToken(refresh_token,client_id=CLIENTID,client_secret=CLIENTSECRET):
  url = "https://api.flumewater.com/oauth/token"
  payload = "{\"grant_type\":\"refresh_token\",\"refresh_token\":\"%s\",\"client_id\":\"%s\",\"client_secret\":\"%s\"}"%\
            (refresh_token,client_id,client_secret)
  headers = {'content-type': 'application/json'}
  response = requests.request("POST", url, data=payload, headers=headers)
  r = json.loads(response.text)
  return r['data'][0]['refresh_token']

#===========================================================================================================
# https://flumetech.readme.io/reference#fetch-single-user
def flumeUserID(access_token):
  url = "https://api.flumewater.com/me" # Magic trick: Let's us using 'JWT Hint" above
  headers = {'authorization': 'Bearer %s'%access_token}
  response = requests.request("GET", url, headers=headers)
  r=json.loads(response.text)
  return r['data'][0]['id']

#===========================================================================================================
# https://flumetech.readme.io/reference#get-a-users-devices
def flumeFirstDeviceID(access_token,user_id):
  url = "https://api.flumewater.com/users/%s/devices"%user_id
  headers = {'authorization': 'Bearer %s'%access_token}
  querystring = {"user":"false","location":"false"}
  response = requests.request("GET", url, params=querystring, headers=headers)
  r = json.loads(response.text)
  for d in r['data']:
    if d['bridge_id'] != None: return d['id']   
  return None

#===========================================================================================================
# https://flumetech.readme.io/reference#query-a-user-device
# https://flumetech.readme.io/docs/querying-samples
def flumeQuery(access_token,user_id,device_id):
  url = "https://api.flumetech.com/users/%s/devices/%s/query"%(user_id,device_id)
  headers = {
    'content-type': 'application/json',
    'authorization': 'Bearer %s'%access_token
  }
  payload = """{ "queries": [{ "request_id": "abc", "bucket": "DAY", "since_datetime": "2020-07-24 01:00:00", "group_multiplier": 3 },"""+\
            """{ "request_id": "pdq", "bucket": "HR", "since_datetime": "2020-07-24 01:00:00"}] }"""
  #          """{ "request_id": "xyz", "bucket": "HR", "since_datetime": "2020-07-24 01:00:00", "until_datetime": "2020-08-01 18:00:00" }] }"""+\
  response = requests.request("POST", url, data=payload, headers=headers)
  r = json.loads(response.text)
  return r

#===========================================================================================================
def flumeGetData():
  # c'est moi
  access_token,refresh_token=flumeTokens()
  # Note; 604800/(3600*24) = 7 days, so maybe need to refresh after 7 days?
  #refresh_token=flumeRefreshToken(refresh_token)
  user_id   = flumeUserID(access_token)
  device_id = flumeFirstDeviceID(access_token,user_id)
  r         = flumeQuery(access_token,user_id,device_id)
  #pprint(r)
  data=r['data'][0]['pdq']
  df = pd.DataFrame(data)
  return df

#===========================================================================================================
def plotWaterUsage(df,plotType='linear'):
  fig = px.bar(df, x="datetime", y="value", title='Water Usage - Scale: '+plotType)
  fig.update_xaxes(
      rangeslider_visible=True,
      rangeselector=dict(
          buttons=list([
              dict(count=1, label="1m", step="month", stepmode="backward"),
              dict(count=6, label="6m", step="month", stepmode="backward"),
              dict(count=1, label="YTD", step="year", stepmode="todate"),
              dict(count=1, label="1y", step="year", stepmode="backward"),
              dict(step="all")
          ])
      )
  )
  fig.update_layout( 
            barmode='group', legend=dict(x=.05, y=0.95, font={'size':15}, bgcolor='rgba(240,240,240,0.5)'), 
            plot_bgcolor='#FFFFFF', font={'size':12, 'color':"rgb(30,30,30)", 'family':"Courier New, monospace"}) \
        .update_yaxes(
            title='Water Usage', showgrid=True, gridcolor='#DDDDDD',
            type=plotType)

  fig.show()

#===========================================================================================================
from pprint import pprint

if __name__ == '__main__':
  df=flumeGetData()
  print(df)
  plotWaterUsage(df)
  plotWaterUsage(df,'log')
