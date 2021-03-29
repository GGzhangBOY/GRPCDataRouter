import grpc
import time
import hashlib
from concurrent import futures
import ProtoGen.AudioCommucation_pb2 as pb2
import ProtoGen.AudioCommucation_pb2_grpc as pb2_grpc

#TODO Add critical mode to ensure data send and response in order
class Router(pb2_grpc.RouterServiceServicer):


    def __init__(self):
        self.max_try_time = 60
        self.PairingFrontend = []
        self.PairingBackend = []
        self.PairedList = []

        """
        PairedList structure:
        Type:dict
        Structure:
        {
            "Hash_id":
            {
                "ModelNum":INT,
                "ModelSet":INT,
                "ShouldClose":bool,
                "Closed":bool(False)
                "Frontend_dataslot":[],
                "Backend_dataslot":[]
            }
        }
        """
        self.PairedDataDict = {}
    
    def __MakePair(self, pair_key):
        index_f = -1
        index_b = -1

        if(pair_key in self.PairingFrontend):
            index_f = self.PairingFrontend.index(pair_key)
        if(pair_key in self.PairingBackend):
            index_b = self.PairingBackend.index(pair_key)

        if(index_f == -1 or index_b == -1):
            return None
        
        session_id = str(hashlib.sha1(str(pair_key).encode("utf8")).hexdigest())
        return session_id
    
    def __PopIte(self, ListIn):
        for i in range(len(ListIn)):
            yield ListIn.pop(0)

    def GetPair(self, request, context):
        local_valid_pair = False
        local_session_id = None


        if(request.Identity):
            self.PairingFrontend.append(request.PairID)
        else:
            self.PairingBackend.append(request.PairID)

        for i in range(self.max_try_time):
            local_session_id = self.__MakePair(request.PairID)
            if(local_session_id is not None):
                local_valid_pair = True
                #Init the dict list element first
                self.PairedDataDict[local_session_id] = {}
                self.PairedDataDict[local_session_id]["Frontend_dataslot"] = []
                self.PairedDataDict[local_session_id]["Backend_dataslot"] = []
                self.PairedDataDict[local_session_id]["Closed"] = False
                if(request.Identity):
                    self.PairedDataDict[local_session_id]["ModelNum"] = None
                else:
                    self.PairedDataDict[local_session_id]["ModelSet"] = -3
                break
            time.sleep(1)
        
        print("Make new session: ",local_session_id)
        return pb2.SessionID(VaildPair = local_valid_pair, SessionID = local_session_id)

    # Choose the model to be used
    def SetModel(self, request, context):

        for i in range(self.max_try_time):
            self.PairedDataDict[request.AdditionalInfo]["ModelNum"] = request.ModelNum
            if("ModelSet" in self.PairedDataDict[request.AdditionalInfo].keys()):
                current_status = self.PairedDataDict[request.AdditionalInfo]["ModelSet"]
                # Backend has not return
                if(current_status >= 0):
                    pass
                
                if(current_status == -1):
                    print("Set model :",request.ModelNum," for session id: ",request.AdditionalInfo)
                    return pb2.StatusResponse(IsSuccess = True, AdditionalInfo="Success, Code -1")
                
                if(current_status == -2):
                    return pb2.StatusResponse(IsSuccess = False, AdditionalInfo="Failed, Code -2")
                
            time.sleep(1)
            
        return pb2.StatusResponse(IsSuccess = False, AdditionalInfo="Max Try Time Reached, Backend not response!(SetModel)")

    def P_GetModel(self, request, context):
        local_model_num = -3
        for i in range(self.max_try_time):
            if(not "ModelNum" in self.PairedDataDict[request.AdditionalInfo].keys()):
                pass
            else:
                local_model_num = self.PairedDataDict[request.AdditionalInfo]["ModelNum"]
                if(local_model_num is not None):
                    # Backend has not return
                    if(local_model_num >= 0):
                        return pb2.StartModelRequest(ModelNum = local_model_num, AdditionalInfo="Success")
            
            time.sleep(1)

        return pb2.StartModelRequest(ModelNum=-1, AdditionalInfo="Max Try Time Reached, Frontend not response!(P_GetModel)")

    def P_SetModeSuccess(self, request, context):
        if(request.IsSuccess):
            self.PairedDataDict[request.AdditionalInfo]["ModelSet"] = -1
        else:
            #Currently additional info only used for start up
            self.PairedDataDict[request.AdditionalInfo]["ModelSet"] = -2

        return pb2.EmptyRequest(AdditionalInfo = "Router Response")

    # client2server stream rpc
    def SendData(self, request_iterator, context): #returns (stream RecognitionResult) {}
        for request in request_iterator:
            print("Receive client data")
            self.PairedDataDict[request.AdditionalInfo]["Frontend_dataslot"].append(request)
            for f_data in self.__PopIte(self.PairedDataDict[request.AdditionalInfo]["Backend_dataslot"]):
                yield pb2.RecognitionResult(Result=f_data.Result, No=f_data.No, AdditionalInfo=f_data.AdditionalInfo)

    def P_SendResult(self, request, context):# returns (stream StatusResponse) 
        print("Receive server response")
        self.PairedDataDict[request.AdditionalInfo]["Backend_dataslot"].append(request)
        return pb2.StatusResponse(IsSuccess = True, AdditionalInfo="Router Response")

    def P_GetData(self, request, context):# returns (stream AudioData) {}
        #When using one direction stream, you need to send while the client is alive, or this function will only trigger once
        while(context.is_active()):
            for f_data in self.__PopIte(self.PairedDataDict[request.AdditionalInfo]["Frontend_dataslot"]):
                yield pb2.AudioData(AudioRawData=f_data.AudioRawData, No=f_data.No, AdditionalInfo=f_data.AdditionalInfo) 
    
    
    def Close(self, request, context):# returns (CloseResponse) {}
        self.PairedDataDict[request.CloseInfo]["ShouldClose"] = request.ShouldClose
        for i in range(self.max_try_time):
            if(self.PairedDataDict[request.AdditionalInfo]["Closed"]):
                return pb2.StatusResponse(IsSuccess = True, AdditionalInfo = "Success")
            time.sleep(1)

        return pb2.StatusResponse(IsSuccess = False, AdditionalInfo = "Max Try Time Reached, Frontend not response!(Close)")


    def P_GetClose(self, request, context):# returns (stream CloseResponse) {}
        current_should_close = self.PairedDataDict[request.AdditionalInfo]["ShouldClose"]
        return pb2.CloseRequest(ShouldClose = current_should_close, AdditionalInfo = "Router Response")
    
    def P_SendCloseResult(self, request, context):# returns (EmptyRequest)  {}
        self.PairedDataDict[request.CloseInfo]["Closed"] = request.ShouldClose
        return pb2.EmptyRequest(AdditionalInfo = "Router Response")

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb2_grpc.add_RouterServiceServicer_to_server(Router(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Server Started!")
    try:
        while True:
            pass # one day in seconds
    except KeyboardInterrupt:
        server.stop(0)

if __name__=="__main__":
    serve()
    