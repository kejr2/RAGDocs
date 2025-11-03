from typing import List, Dict


def format_basic_answer(sources: List[Dict]) -> str:
    """Fallback answer formatting when Gemini is not available."""
    answer_parts = ["Based on the retrieved documentation:\n"]
    
    for i, source in enumerate(sources[:3], 1):
        heading = source['metadata'].get('heading', 'Document')
        source_type = source['metadata'].get('type', 'text')
        
        if source_type == "code":
            language = source['metadata'].get('language', '')
            answer_parts.append(f"\n**Source {i}** ({heading}):")
            answer_parts.append(f"```{language}\n{source['content']}\n```")
        else:
            answer_parts.append(f"\n**Source {i}** ({heading}):")
            answer_parts.append(
                source['content'][:300] + "..." 
                if len(source['content']) > 300 
                else source['content']
            )
    
    return "\n".join(answer_parts)

