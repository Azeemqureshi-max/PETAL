from shared_llm import generate


NOT_FOUND = "[ANSWER_NOT_FOUND]"


def answer_from_page(question, page_text):

    page_text = page_text[:10000]

    messages = [
        {
            "role": "system",
            "content": (
                "You are Petal's web research engine.\n"
                "Answer the user's question using ONLY "
                "information explicitly present in the webpage "
                "content provided below.\n\n"
                "Do not use your own memory.\n"
                "Do not add outside facts.\n"
                "Do not guess.\n"
                "Do not fill missing information from general knowledge.\n\n"
                "If the webpage does not contain enough information "
                "to answer the question, return exactly:\n"
                "[ANSWER_NOT_FOUND]\n\n"
                "If the webpage does contain enough information, "
                "give a concise and useful answer."
            )
        },
        {
            "role": "user",
            "content": (
                f"Question:\n{question}\n\n"
                f"Webpage content:\n{page_text}"
            )
        }
    ]

    answer = generate(
        messages,
        max_new_tokens=300,
        temperature=0.1
    )

    if not answer:
        return NOT_FOUND

    return answer.strip()


if __name__ == "__main__":

    question = (
        "What programming language is this website about?"
    )

    page = (
        "Python.org is the official website "
        "for the Python programming language."
    )

    answer = answer_from_page(
        question,
        page
    )

    print(answer)