#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 24 16:34:14 2020

@author: tefirman
"""

import dash
from dash import dcc
from dash import html
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pandas as pd
import datetime
import plotly.graph_objs as go

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = '1EXnnJkVHObBsVdXg2JeTylRxVt9wQyEPZMIOhMJvkDU'

def get_creds():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return creds

def get_values(rangeVals):
    service = build('sheets', 'v4', credentials=get_creds())
    values = service.spreadsheets().values().get(\
    spreadsheetId=SPREADSHEET_ID,range=rangeVals)\
    .execute().get('values', [])
    return pd.DataFrame(values[1:],columns=values[0])

def put_values(rangeVals,values):
    service = build('sheets', 'v4', credentials=get_creds())
    body = {'range':rangeVals,'majorDimension':"ROWS",'values':values}
    service.spreadsheets().values().update(spreadsheetId=SPREADSHEET_ID,\
    range=rangeVals,valueInputOption='USER_ENTERED',body=body).execute()

questions = get_values('Questions!A1:D1000')
current_question = questions.loc[questions.Active == 'TRUE']

def add_response(team,question,answer,wager):
    responses = get_values('Responses!A1:F1000')
    put_values("Responses!A" + str(responses.shape[0] + 2) + ":F" + \
    str(responses.shape[0] + 2),[[team,str(datetime.datetime.now()),question,answer,wager,'Unscored']])

standings = pd.DataFrame(columns=['Team Name','Score','Unscored'])
fig = go.Figure(data=[go.Table(columnwidth=[100,50,50],header=dict(values=list(standings.columns),\
fill_color='paleturquoise',align='center'),cells=dict(values=[standings['Team Name'],\
standings['Score'],standings['Unscored']],fill_color='lavender',align='center'))])

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server
app.layout = html.Div([
    html.H1('Trivia: Quarantine Style'),
    html.Div(id='question-container',children=current_question.Question.values[0]),
    html.Div(dcc.Input(id='input-team', type='text',placeholder="Team Name",size=35)),
    html.Div(dcc.Input(id='input-answer', type='text',placeholder="Response",size=35)),
    html.Div(dcc.Input(id='input-wager', type='text',placeholder="Wager",size=35)),
    html.Button('Submit', id='submit-button'),
    html.Div(id='output-container-button',children="Let's get started!!!"),
    html.Div([dcc.Graph(id='standings-table',figure=fig)], \
    style={'width': '75%', 'display': 'inline-block', 'padding': '0 20'}),
    dcc.Interval(id='interval-component',interval=30*1000,n_intervals=0)
])

@app.callback(
    [dash.dependencies.Output('output-container-button', 'children'),
    dash.dependencies.Output('input-answer', 'value'),
    dash.dependencies.Output('input-wager', 'value')],
    [dash.dependencies.Input('submit-button','n_clicks')],
    [dash.dependencies.State('input-team','value'),
    dash.dependencies.State('input-answer','value'),
    dash.dependencies.State('input-wager','value')])
def update_output(n_clicks, team, answer, wager):
    if n_clicks is not None:
        add_response(team,current_question.Number.values[0],answer,wager)
        return '"{}" just answered "{}" and wagered {}.'.format(team,answer,wager,n_clicks),'',''

@app.callback(
    [dash.dependencies.Output('question-container', 'children'),
    dash.dependencies.Output('standings-table', 'figure')],
    [dash.dependencies.Input('interval-component','n_intervals')])
def update_question(n_intervals):
    global current_question
    questions = get_values('Questions!A1:D1000')
    responses = get_values('Responses!A1:F1000')
    responses = responses.loc[responses.Wager.str.isnumeric()].reset_index(drop=True)
    responses.Wager = responses.Wager.astype(int)
    standings = pd.merge(left=pd.merge(left=pd.DataFrame({'Team Name':responses['Team Name'].unique()}),\
    right=responses.loc[responses.Scoring == 'Correct'].groupby('Team Name').Wager.sum()\
    .reset_index().rename(columns={'Wager':'Score'}),how='left',on='Team Name'),\
    right=responses.loc[responses.Scoring == 'Unscored'].groupby('Team Name')\
    .size().to_frame('Unscored').reset_index(),how='left',on='Team Name')
    standings.Score = standings.Score.fillna(0)
    standings.Unscored = standings.Unscored.fillna(0)
    standings = standings.sort_values(by='Score',ascending=False).reset_index(drop=True)
    fig = go.Figure(data=[go.Table(columnwidth=[100,50,50],header=dict(values=list(standings.columns),\
    fill_color='paleturquoise',align='center'),cells=dict(values=[standings['Team Name'],\
    standings['Score'],standings['Unscored']],fill_color='lavender',align='center'))])
    current_question = questions.loc[questions.Active == 'TRUE']
    return current_question['Question'].values[0], fig

if __name__ == '__main__':
    app.run_server()




