import ProtoGen.AudioCommucation_pb2 as pb2
import ProtoGen.AudioCommucation_pb2_grpc as pb2_grpc
import numpy as np
import grpc
import time
import StreamingAudio

__TIME_OUT_SEC = 120
__GLOBAL_COUNTER = 0
def AudioDataGetter(In_AdditionalInfoInfo):
    while True:
        if(len(StreamingAudio.cache_raw_data_int_list)==0):
            continue
        data = StreamingAudio.cache_raw_data_int_list.popleft()
        __GLOBAL_COUNTER += 1
        yield pb2.AudioData(No=__GLOBAL_COUNTER,AdditionalInfo=In_AdditionalInfoInfo,AudioRawData=data)

def run():
    # Connect to grpc server
    start_time1 = time.time()
    channel = grpc.insecure_channel('localhost:50051')

    grpc.channel_ready_future(channel).result(timeout=__TIME_OUT_SEC)
    # Call rpc service
    stub = pb2_grpc.RouterServiceStub(channel)

    # Pairing
    PairInfoRef = stub.GetPair(pb2.PairInfo(Identity=True, PairID="Rec"))

    if(not PairInfoRef.VaildPair):
        print("Invalid Pair")
        return
    
    print(PairInfoRef.SessionID)
    SetModelResponseRef = stub.SetModel(pb2.StartModelRequest(ModelNum=0, AdditionalInfo=PairInfoRef.SessionID))
    
    if(not SetModelResponseRef.IsSuccess):
        print(SetModelResponseRef.AdditionalInfo)
        return
    
    print("Set Sender!")

    RecResults = stub.SendData(AudioDataGetter(PairInfoRef.SessionID))
    print(RecResults)
    time.sleep(1)
    
    while True:
        for result in RecResults:
            print(result.Result)

 
 
if __name__ == '__main__':
    StreamingAudio.Run(1)
    run()

