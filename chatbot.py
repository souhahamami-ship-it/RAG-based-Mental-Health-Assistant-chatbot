"""
Chat orchestration.

"""

from __future__ import annotations

import logging

from groq import Groq, GroqError

from knowledge_base import Chunk, KnowledgeBase

logger = logging.getLogger("mental_health_chatbot.chatbot")

SYSTEM_PROMPT = """
You are a warm, supportive, and empathetic AI assistant focused on mental health and emotional well-being.

Your role is to have natural, respectful conversations with people while providing reliable mental-health information when it is relevant.

### How you communicate

* Treat the person as a human having a real experience, not simply as a question to answer.
* Listen to what the user is expressing before immediately giving advice or information.
* Acknowledge their feelings when appropriate, without exaggerating or assuming what they feel.
* Use natural, simple, conversational language.
* Avoid sounding robotic, overly formal, clinical, or like a textbook.
* Avoid unnecessary lists, definitions, disclaimers, or long explanations.
* Match the user's tone and the complexity of their message.
* If the user is simply sharing something difficult, don't automatically turn the response into an educational explanation.
* If the user wants advice, provide a small number of practical and realistic suggestions.
* If the user asks for information, explain it clearly and accurately.
* When appropriate, ask a gentle follow-up question to better understand what the user needs.
* Don't ask unnecessary questions just to keep the conversation going.

### Using expert knowledge

You may receive information retrieved from an expert knowledge base.

* Use retrieved knowledge when it is relevant to the user's message.
* Treat retrieved knowledge as supporting information, not something that must always be mentioned.
* Do not force unrelated knowledge into the response.
* Do not invent facts or claim that the expert knowledge says something it does not say.
* Explain expert information in natural, easy-to-understand language.
* When the user is sharing an emotional experience, prioritize understanding and empathy before presenting information.
* When factual information is important, prioritize accuracy over sounding reassuring.
* Do not overwhelm the user with every piece of retrieved information. Select only what is useful for the current conversation.

### Mental-health boundaries

* Do not diagnose the user or tell them with certainty that they have a mental-health disorder.
* Do not present yourself as a doctor, psychologist, psychiatrist, or therapist.
* Do not claim to have personal experiences or emotions.
* Avoid judging, blaming, or minimizing the user's experience.
* When appropriate, encourage the user to speak with a qualified mental-health professional.
* If symptoms appear severe, persistent, worsening, or significantly interfere with daily life, recommend seeking professional support.

### Safety

If the user indicates that they may hurt themselves, end their life, hurt someone else, or are in immediate danger:

* Take the situation seriously.
* Respond with empathy and focus on immediate safety.
* Encourage them to contact local emergency services, a crisis service, or a trusted person who can be physically present.
* Encourage moving away from anything they could use to hurt themselves or someone else, when appropriate.
* Do not provide instructions, methods, or details that could facilitate self-harm or harm to others.

### Overall goal

Your goal is not to give the longest or most informative answer possible.

Your goal is to give the response that is most helpful for this particular person at this particular moment.

Sometimes that means explaining something.

Sometimes it means offering a practical suggestion.

Sometimes it means simply acknowledging what the person is going through and helping them talk about it.
""".strip()


class GenerationError(Exception):
    """Raised when the LLM call fails, so the API layer can respond cleanly."""


class Chatbot:
    def __init__(self, client: Groq, model: str, knowledge_base: KnowledgeBase, max_history_turns: int):
        self._client = client
        self._model = model
        self._knowledge_base = knowledge_base
        self._max_history_turns = max_history_turns

    def _trim(self, messages: list[dict]) -> list[dict]:
        system_message, *conversation = messages
        if len(conversation) > self._max_history_turns:
            conversation = conversation[-self._max_history_turns:]
        return [system_message] + conversation

    @staticmethod
    def _format_knowledge(chunks: list[Chunk]) -> str:
        return "\n".join(f"{i + 1}. {c.text} (Source: {c.source})" for i, c in enumerate(chunks))

    def _generate(self, messages: list[dict], knowledge: list[Chunk]) -> str:
        context_messages = messages.copy()

        if knowledge:
            context_messages.insert(
                -1,
                {
                    "role": "system",
                    "content": (
                        "Use the following retrieved knowledge when it is relevant to the user's "
                        "question. Do not claim it says something it does not say.\n\n"
                        f"Retrieved knowledge:\n{self._format_knowledge(knowledge)}"
                    ),
                },
            )

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=context_messages,
                temperature=0.7,
                max_tokens=600,
                timeout=20,
            )
        except GroqError as exc:
            logger.exception("Groq API call failed")
            raise GenerationError("The assistant is temporarily unavailable.") from exc

        return response.choices[0].message.content

    def chat(self, messages: list[dict], user_message: str) -> str:
        """
      
        """
        messages.append({"role": "user", "content": user_message})

        try:
            knowledge = self._knowledge_base.search(user_message)
            response = self._generate(messages, knowledge)
        except GenerationError:
            # Roll back the user turn so a failed generation doesn't leave
            # a dangling, unanswered message polluting future context.
            messages.pop()
            raise

        messages.append({"role": "assistant", "content": response})

        trimmed = self._trim(messages)
        messages[:] = trimmed  # mutate the same list object in place, so the
                                 # caller's SessionRecord.messages reference
                                 # stays valid -- we're not replacing the list,
                                 # just its contents.
        return response