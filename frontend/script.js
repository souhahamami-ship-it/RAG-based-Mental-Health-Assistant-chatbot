const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const chatMessages = document.getElementById("chat-messages");
const sendButton = document.getElementById("send-button");
let sessionBlocked = false;
let isSending = false;          // ADD THIS LINE
/*
    Create one session ID for this browser session.
*/


let sessionId = sessionStorage.getItem("session_id");      // AFTER


if (!sessionId) {
    sessionId = crypto.randomUUID();
    sessionStorage.setItem("session_id", sessionId); 
}

console.log("Session ID:", sessionId);


/*
    Add a message to the chat.
*/

function addMessage(message, sender) {

    const messageElement = document.createElement("div");

    messageElement.classList.add("message");

    if (sender === "user") {
        messageElement.classList.add("user-message");
    } else {
        messageElement.classList.add("bot-message");
    }

    const paragraph = document.createElement("p");

    paragraph.textContent = message;

    messageElement.appendChild(paragraph);

    chatMessages.appendChild(messageElement);

    chatMessages.scrollTop = chatMessages.scrollHeight;
}


/*
    Send message to FastAPI.
*/

async function sendMessage(message) {

    console.log("Sending with session:", sessionId);

    const response = await fetch(
        "http://127.0.0.1:8000/chat",
        {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                session_id: sessionId,
                message: message
            })
        }
    );

    if (!response.ok) {
        throw new Error("Server error");
    }

    const data = await response.json();

    // Display bot response
    addMessage(data.response, "bot");


    // Check if session is blocked
    if (data.blocked === true) {

        sessionBlocked = true;

        messageInput.disabled = true;
        sendButton.disabled = true;

        messageInput.placeholder = "This conversation has been ended for safety reasons.";

        console.log("Session blocked.");
    }
}


/*
    Handle form submission.
*/

chatForm.addEventListener("submit", async (event) => {

    event.preventDefault();
    // Do nothing if session is blocked
    if (sessionBlocked || isSending) {
        return;
    }


    const message = messageInput.value.trim();

    if (!message) {
        return;
    }


    // Show user's message
    addMessage(message, "user");

    // Clear input
    messageInput.value = "";

    // Disable send button
    isSending = true;
sendButton.disabled = true;
messageInput.disabled = true;


    try {

        await sendMessage(message);

    } catch (error) {

        console.error(error);

        addMessage(
            "I'm sorry, something went wrong. Please try again.",
            "bot"
        );

    }


    isSending = false;

if (!sessionBlocked) {
    sendButton.disabled = false;
    messageInput.disabled = false;
    messageInput.focus();}
});