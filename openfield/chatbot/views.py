from rest_framework import status
from rest_framework.response import Response
from langchain.chat_models import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.memory import ConversationBufferMemory
from .models import UsageLog
from rest_framework.views import APIView



class ChatAPIView(APIView):

    count = 0
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs) # APIView를 상속받기 때문에 부모 클래스의 생성자를 호출, 초기화
        self.chat_model = None
        self.database = None
        self.qa = None

    def initialize_models(self):
        if self.chat_model is None:
            # ChatOpenAI 모델 초기화
            self.chat_model = ChatOpenAI(model="gpt-3.5-turbo")
        
        if self.database is None:
            # Chroma 데이터베이스 초기화
            embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
            self.database = Chroma(persist_directory="./database", embedding_function=embeddings)
            
            # RetrievalQA 초기화
            k = 3
            retriever = self.database.as_retriever(search_kwargs={"k": k})
            memory = ConversationBufferMemory(memory_key="chat_history", input_key="question", output_key="result",
                                              return_messages=True)
            self.qa = RetrievalQA.from_llm(llm=self.chat_model, retriever=retriever, memory=memory,
                                           input_key="question", output_key="result", return_source_documents=True)
    
    
    def post(self, request):
        
        # 모델 초기화
        self.initialize_models()
        
        # 세션을 가져오거나 새로 생성합니다.
        session_key = request.session.session_key
        
        if not session_key:
            request.session.save()
        
        # 대화 기록을 세션에서 가져옵니다.
        chat_history = request.session.get('chat_history', [])

        # 사용자의 질문을 가져옵니다.
        query = request.data.get('question')
        #print("query:",query)
        
        
        if query != '' :
            print("count1:",ChatAPIView.count)
            if self.database.get()['ids'] is not None:    
                score = self.database.similarity_search_with_score(query)[0][1] # 유사도가 가장 높은 Document 중 유사도 점수만 선택
                if score > 0.2:  # 코사인 유사도 0에 가까울 수록 유사도가 높음. 유사도가 높지 않은 질문을 할 수록 count증가
                    ChatAPIView.count += 1
                    #print("count:",ChatAPIView.count)
                    if ChatAPIView.count == 3:
                        
                        response = Response({'result': 'irrelevant'}, status=status.HTTP_200_OK)
                        ChatAPIView.count = 0 # count 초기화
                        
                        return response
        else:
            return Response({'error': 'No questions.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 대화 기록에 질문을 추가합니다.
        chat_history.append({'user': query})

        # 대화 기록을 업데이트합니다.
        request.session['chat_history'] = chat_history

        # ChatOpenAI의 모델을 사용하여 적절한 답변을 생성합니다.
        result = self.qa.invoke({"question": query, "chat_history": chat_history})

        # 대화 기록에 봇의 답변을 추가합니다.
        chat_history.append({'bot': result['result']})

        # 대화 기록을 업데이트합니다.
        request.session['chat_history'] = chat_history

        UsageLog.objects.create(question=query, answer=result["result"])
        # 클라이언트에 대답을 반환합니다.
        response = Response({'result': result['result']}, status=status.HTTP_200_OK)
        return response   
        


class SessionClearAPIView(APIView):
    def get(self, request):
        request.session.flush()
        return Response({'status': 'success', 'message': 'Session cleared successfully.'})
