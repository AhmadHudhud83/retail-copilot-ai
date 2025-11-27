import dspy

# --- 1. Router ---
class RouterSignature(dspy.Signature):
    """
    Classify the question.
    RULES:
    1. 'rag_only': Questions about 'policy', 'return', 'days', 'definitions'.
    2. 'sql_only': Questions requiring calculation (SUM, COUNT, AVG) on the database.
    3. 'hybrid': specific data queries filtered by a named event (e.g. "Summer 1997").
    """
    question = dspy.InputField()
    classification = dspy.OutputField(desc="rag_only, sql_only, or hybrid")

# --- 2. SQL Generator (The Brain) ---
class TextToSQL(dspy.Signature):
    """
    You are a SQLite expert. Your only task is to generate a valid SQL query
    that answers the question based on the schema_context and context.
    Do NOT invent or assume any final numeric values.
    Only produce the SQL query string.
    """
    question = dspy.InputField(
        desc="The question to translate into SQL"
    )
    schema_context = dspy.InputField(
        desc="Dictionary of table names to their column names"
    )
    context = dspy.InputField(
        desc="Additional constraints, business rules, or notes from docs",
        format=str
    )
    sql_query = dspy.OutputField(
        desc="Valid SQLite query string; do NOT include hardcoded answers or values"
    )


# --- 3. Synthesizer (The Mouth) ---
class GenerateAnswer(dspy.Signature):
    """
    Answer the question based on the tools.
    - If format_hint is 'int' or 'float', return ONLY the number in 'final_answer'.
    - If format_hint is 'json' or 'list', ensure valid JSON syntax.
    """
    question = dspy.InputField()
    sql_query = dspy.InputField()
    sql_result = dspy.InputField()
    doc_context = dspy.InputField()
    format_hint = dspy.InputField()
    
    explanation = dspy.OutputField(desc="Brief explanation")
    final_answer = dspy.OutputField(desc="The precise answer matching format_hint")
    citations = dspy.OutputField(desc="List of tables/docs used")

# --- 4. Planner ---
class ExtractSearchTerms(dspy.Signature):
    """Extract search terms."""
    question = dspy.InputField()
    search_queries = dspy.OutputField(desc="List of strings")