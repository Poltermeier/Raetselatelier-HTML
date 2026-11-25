"""Small local preferences and synthesized game sounds."""
from functools import lru_cache
import io
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import wave

DEFAULTS={'volume':15,'colorblind':False}


def preferences_path():
    base=Path(os.environ.get('APPDATA') or Path.home()/'AppData'/'Roaming') if sys.platform=='win32' else Path(os.environ.get('XDG_CONFIG_HOME') or Path.home()/'.config')
    return base/'Simons-Raetselatelier'/'settings.json'


def normalize_preferences(values):
    values=values if isinstance(values,dict) else {}
    volume=values.get('volume',DEFAULTS['volume'])
    if type(volume) is not int and (type(volume) is not float or not math.isfinite(volume)):volume=DEFAULTS['volume']
    return dict(volume=max(0,min(100,round(volume))),colorblind=values.get('colorblind') is True)


def load_preferences(path=None):
    try:
        with Path(path or preferences_path()).open(encoding='utf-8') as stream:return normalize_preferences(json.load(stream))
    except (OSError,ValueError,TypeError):return DEFAULTS.copy()


def save_preferences(values,path=None):
    target=Path(path or preferences_path());temporary=None
    try:
        target.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=target.parent,delete=False) as stream:
            temporary=Path(stream.name);json.dump(normalize_preferences(values),stream,ensure_ascii=False)
        os.replace(temporary,target);return True
    except OSError:return False
    finally:
        if temporary is not None:
            try:temporary.unlink(missing_ok=True)
            except OSError:pass


@lru_cache(maxsize=32)
def sound_wave(volume, notes):
    rate=22050;pcm=bytearray();amplitude=round(12000*max(0,min(100,volume))/100)
    for frequency,duration in notes:
        count=round(rate*duration)
        for i in range(count):
            envelope=min(1,i/(rate*.008),(count-i)/(rate*.035))
            pcm.extend(struct.pack('<h',round(amplitude*envelope*math.sin(2*math.pi*frequency*i/rate))))
    stream=io.BytesIO()
    with wave.open(stream,'wb') as sound:
        sound.setnchannels(1);sound.setsampwidth(2);sound.setframerate(rate);sound.writeframes(pcm)
    return stream.getvalue()



def victory_wave(volume):
    return sound_wave(volume, ((523.25, .09), (659.25, .09), (783.99, .17)))


class VictorySound:
    def __init__(self):self.thread=None

    def play(self, volume, *, frequency=None, duration=.19):
        volume = normalize_preferences({"volume": volume})["volume"]
        if not volume:
            return
        if frequency is not None:
            threading.Thread(target=self._play, args=(volume, frequency, duration), daemon=True).start()
            return
        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=self._play, args=(volume,), daemon=True)
            self.thread.start()

    @staticmethod
    def _play(volume, frequency=None, duration=.19):
        try:
            data=victory_wave(volume) if frequency is None else sound_wave(volume, ((frequency, duration),))
            if sys.platform=='win32':
                import winsound
                winsound.PlaySound(data,winsound.SND_MEMORY|winsound.SND_NODEFAULT)
            elif shutil.which('aplay'):
                subprocess.run(['aplay','-q'],input=data,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=3)
            elif sys.platform=='darwin' and shutil.which('afplay'):
                with tempfile.NamedTemporaryFile(suffix='.wav') as stream:
                    stream.write(data);stream.flush()
                    subprocess.run(['afplay',stream.name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=3)
        except (ImportError,OSError,RuntimeError,subprocess.SubprocessError):pass
