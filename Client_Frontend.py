import ProtoGen.AudioCommucation_pb2 as pb2
import ProtoGen.AudioCommucation_pb2_grpc as pb2_grpc
import grpc
import time

__TIME_OUT_SEC = 120
def AudioDataGetter(In_AdditionalInfoInfo):
    while True:
        yield pb2.AudioData(No=0,AdditionalInfo=In_AdditionalInfoInfo,AudioRawData=[1,2,3,4,5])

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
    run()

