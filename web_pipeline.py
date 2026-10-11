
from web_tool import search_web
from web_reader import read_web_page
from web_answer import answer_from_page, NOT_FOUND


def research_web(question):
    question = question.strip()

    if not question:
        return {
            "question": question,
            "answer": "Please tell me what you want me to research.",
            "sources": [],
            "research_status": "failed"
        }

    search_result = search_web(question, max_results=5)
    results = search_result.get("results", [])
    search_error = search_result.get("error")

    if not results:
        if search_error:
            answer = (
                "I couldn't reach the web search service. "
                f"Details: {search_error}"
            )
            status = "failed"
        else:
            answer = (
                "The search returned no usable results. "
                "Try again when your internet connection is stable."
            )
            status = "no_results"

        return {
            "question": question,
            "answer": answer,
            "sources": [],
            "research_status": status
        }

    sources = []
    findings = []
    seen_urls = set()
    pages_read = 0

    for result in results:
        title = result.get("title", "").strip()
        url = result.get("url", "").strip()

        if not url or url in seen_urls:
            continue

        seen_urls.add(url)

        page_text = read_web_page(url)

        if not page_text:
            continue

        if page_text.startswith("[WEB READER ERROR]"):
            continue

        if len(page_text.strip()) < 200:
            continue

        pages_read += 1

        answer = answer_from_page(question, page_text)

        if not answer or NOT_FOUND in answer:
            continue

        answer = answer.strip()

        if not answer:
            continue

        sources.append({
            "title": title or "Untitled webpage",
            "url": url
        })

        findings.append({
            "title": title or "Untitled webpage",
            "url": url,
            "answer": answer
        })

    if not findings:
        if pages_read == 0:
            answer = (
                "I found search results, but couldn't read any "
                "of the webpages. Check your internet connection "
                "or try again later."
            )
            status = "read_failed"
        else:
            answer = (
                "I read the available webpages, but couldn't "
                "find enough information to answer confidently."
            )
            status = "insufficient_evidence"

        return {
            "question": question,
            "answer": answer,
            "sources": [],
            "research_status": status
        }

    # Keep individual findings visible instead of asking the
    # small model to invent a consensus between different pages.
    answer_parts = []

    for finding in findings:
        answer_parts.append(
            f"• {finding['answer']}\n"
            f"  Source: {finding['title']}\n"
            f"  URL: {finding['url']}"
        )

    combined_answer = (
        f"Web research for: {question}\n\n"
        + "\n\n".join(answer_parts)
        + "\n\nNote: These are findings from individual webpages. "
          "Check the sources, especially if they disagree."
    )

    return {
        "question": question,
        "answer": combined_answer,
        "sources": sources,
        "research_status": "complete"
    }
