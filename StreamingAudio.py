import pyaudio
import yaml
import threading
import os
import copy
import audioop
import webrtcvad
import wave
import time

from queue import deque

cache_file_list = deque()
cache_raw_data_list = deque()
cache_raw_data_int_list = deque()

worker_stop_flag = False

mutex = threading.Lock()

global_ticker = 0

class StreamAudio:
    def __init__(self,conf_file:yaml, max_concat_frames = 10):
        self.currentCacheFile = ""
        self.streaming_configs = conf_file.get('streaming_conf',{})
        self.WorkerReader = WorkerMicReader(stream_audio_conf=self.streaming_configs)
        self.WorkerCacher = WorkerCacheMaker(stream_audio_conf=self.streaming_configs)
        self.test_collate_conf = copy.deepcopy(conf_file['collate_conf'])
        self.test_collate_conf['spec_aug'] = False
        self.test_collate_conf['spec_sub'] = False
        self.test_collate_conf['feature_dither'] = False
        self.test_collate_conf['speed_perturb'] = False
        #Disable wav distortion for now
        self.test_collate_conf['wav_distortion_conf']['wav_distortion_rate'] = 0
        self.max_concat_frames = max_concat_frames
        
    
    def ResetRecording(self):
        cache_file_list = deque()
        cache_raw_data_list = deque()
        worker_stop_flag = True
        global_ticker = 0

    def StartRecording(self,ModeNum = 0):
        worker_stop_flag = False
        if(ModeNum == 0 or ModeNum == 2):
            self.WorkerCacher.start()
        if(ModeNum == 0 or ModeNum == 1):
            self.WorkerReader.start()
    
    def RequireLatestCacheFiles(self):
        cache_to_return = cache_file_list.popleft()
        self.currentCacheFile = cache_to_return
        return cache_to_return

    def ClearLatestCacheFiles(self):
        if(os.path.exists(self.currentCacheFile)):
            os.remove(self.currentCacheFile)
    
    def EndRecording(self):
        for num,cache in cache_file_list:
            os.remove(cache)
        self.WorkerCacher.stop()
        self.WorkerReader.stop()
    
    def GetAudioFeature(self):
        stop_flag = 10 if len(cache_file_list)>10 else len(cache_file_list)
        current_buffer_list = []

        for i in range(stop_flag):
            current_buffer_list.append(cache_file_list.popleft())

        keys, feats, lengths = _extract_feature(current_buffer_list,**self.test_collate_conf)

        for cache in current_buffer_list:
            if(os.path.exists(self.cache)):
                os.remove(self.cache)

        return keys, feats, lengths


class WorkerMicReader(threading.Thread):
    def __init__(self, stream_audio_conf, thread_name="mic reader"):
        threading.Thread.__init__(self)
        self.name = thread_name
        self.stream_audio_conf = stream_audio_conf
        self._stop_event = threading.Event()

    def run(self):
        CHUNK = int(self.stream_audio_conf['frame_length']/(1/self.stream_audio_conf['sample_rate']*1000)*32)
        FORMAT = pyaudio.paInt32

        CHANNELS = 1
        RATE = self.stream_audio_conf['sample_rate']

        p = pyaudio.PyAudio()
        vad = webrtcvad.Vad(0)

        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)

        while(1):
            if(worker_stop_flag):
                pass
            if(self._stop_event.is_set()):
                break
            data = stream.read(CHUNK)

            should_reject = False
            try:
                #A frame must be either 10, 20, or 30 ms in duration while using webrtcvad
                #To Do
                should_reject = not vad.is_speech(data,RATE)
            except:
                should_reject = False

            if(should_reject):
                pass

            else:
                int_data = []
                for i in data[:]:
                    int_data.append(i)
                #cache_raw_data_list.append(data)
                cache_raw_data_int_list.append(int_data)
    
    def stop(self):
        self._stop_event.set()
 
    def stopped(self):
        return self._stop_event.is_set()


class WorkerCacheMaker(threading.Thread):
    def __init__(self, stream_audio_conf, thread_name="CacheMaker"):
        threading.Thread.__init__(self)
        self.name = thread_name
        self.stream_audio_conf = stream_audio_conf
        self._stop_event = threading.Event()

    def run(self):
        global global_ticker
        global worker_stop_flag
        global cache_file_list
        global cache_raw_data_list

        FORMAT = pyaudio.paInt32

        CHANNELS = 2
        RATE = self.stream_audio_conf['sample_rate']
        
        while(1):
            if( worker_stop_flag or len(cache_raw_data_int_list)==0):
                continue
            if(self._stop_event.is_set()):
                break
            
            WAVE_OUTPUT_FILENAME = os.path.join(self.stream_audio_conf['target_path'],"Cache_"+str(global_ticker)+".wav")
            p = pyaudio.PyAudio()
            wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            frame = bytes(cache_raw_data_int_list.popleft())
            wf.writeframes(frame)
            wf.close()

            cache_file_list.append([global_ticker, WAVE_OUTPUT_FILENAME])
            global_ticker += 1

    def stop(self):
        self._stop_event.set()
 
    def stopped(self):
        return self._stop_event.is_set()

def Run(ModeNum = 0):
    fs = open('D:\mllearn\wenet-main\examples/aishell\s0\conf/train_conformer.yaml')
    conf = yaml.load(fs)
    sm = StreamAudio(conf)
    sm.StartRecording(ModeNum)

if __name__ == "__main__":
    fs = open('D:\mllearn\wenet-main\examples/aishell\s0\conf/train_conformer.yaml')
    conf = yaml.load(fs)
    sm = StreamAudio(conf)
    sm.StartRecording()

    test_stop = threading.Timer(10, sm.EndRecording)
    test_stop.start()