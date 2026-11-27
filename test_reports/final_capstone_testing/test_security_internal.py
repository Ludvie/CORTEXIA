"""Source-directed checks of upload boundaries, cleanup, and validation."""
import asyncio, io
from pathlib import Path
import pytest
from common import *
from fastapi import UploadFile, HTTPException
from pydantic import ValidationError
import sessions

@pytest.mark.parametrize('size,status', [(0,422),(99,422),(25*1024*1024+1,413)])
def test_upload_limits(size,status):
    upload=UploadFile(file=io.BytesIO(b'x'*size),filename='synthetic.audio')
    with pytest.raises(HTTPException) as caught:asyncio.run(sessions.audio_result(upload))
    assert caught.value.status_code==status

@pytest.mark.parametrize('failure',[False,True])
def test_temporary_audio_cleanup(monkeypatch,failure):
    seen=[]
    async def work(fn,path,reference):
        seen.append(Path(path));assert seen[-1].exists()
        if failure:raise ValueError('synthetic decode failure')
        return dict(transcript='test',words=[])
    monkeypatch.setattr(sessions,'run_in_threadpool',work)
    upload=UploadFile(file=io.BytesIO(b'x'*128),filename='synthetic.audio')
    if failure:
        with pytest.raises(HTTPException):asyncio.run(sessions.audio_result(upload))
    else:assert asyncio.run(sessions.audio_result(upload))['transcript']=='test'
    assert seen and not any(p.exists() for p in seen)

@pytest.mark.parametrize('field,value',[('x',float('nan')),('y',float('inf')),('t',-1),('x',11)])
def test_gaze_schema_rejects_invalid(field,value):
    d=dict(x=.5,y=.5,t=0);d[field]=value
    with pytest.raises(ValidationError):sessions.GazePoint(**d)

def test_corrupt_audio_is_rejected_without_temp_leak():
    upload=UploadFile(file=io.BytesIO(b'invalid audio'*100),filename='bad.wav')
    with pytest.raises(HTTPException) as caught:asyncio.run(sessions.audio_result(upload))
    assert caught.value.status_code==422
