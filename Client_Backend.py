import ProtoGen.AudioCommucation_pb2 as pb2
import ProtoGen.AudioCommucation_pb2_grpc as pb2_grpc

import ProtoGen.AudioCommucation_pb2 as pb2
import ProtoGen.AudioCommucation_pb2_grpc as pb2_grpc
import grpc
import time

def AudioDataStorer(Data_In):
    while True:
        yield pb2.AudioData(AudioRawData=[1,2,3,4,5])

def run():
    # Connect to grpc server
    start_time1 = time.time()
    channel = grpc.insecure_channel('localhost:50051')
    # Call rpc service
    stub = pb2_grpc.RouterServiceStub(channel)

    # Pairing
    PairInfoRef = stub.GetPair(pb2.PairInfo(Identity=False, PairID="Rec"))

    if(not PairInfoRef.VaildPair):
        print("Invalid Pair")
        return

    print(PairInfoRef.SessionID)
    SetModelResponseRef = stub.P_GetModel(pb2.EmptyRequest(AdditionalInfo=PairInfoRef.SessionID))
    Router_Set_Model_Response = stub.P_SetModeSuccess(pb2.StatusResponse(IsSuccess=True,AdditionalInfo=PairInfoRef.SessionID))
    
    Data_Ite = stub.P_GetData(pb2.GetDataRequest(AdditionalInfo = PairInfoRef.SessionID))

    while True:
        for Data in Data_Ite:
            print(Data)
            stub.P_SendResult(pb2.RecognitionResult(No=0,AdditionalInfo=PairInfoRef.SessionID,Result="Test"))
 
 
if __name__ == '__main__':
    run()