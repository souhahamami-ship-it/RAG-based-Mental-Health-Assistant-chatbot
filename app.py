from chatbot import Chatbot

chatbot = Chatbot()

while True:
    user_message = input("You: ")

    if user_message == "exit":
        break

    response = chatbot.chat(user_message)

    print(response)