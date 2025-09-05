from fastapi import FastAPI, Body
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from hyperon import MeTTa, Atom
from hyperonpy import AtomKind
from typing import List, Dict, Any
from pydantic import BaseModel 
import os
import json
import re  
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Family Tree API",
    description="An API to query a family tree knowledge base using MeTTa logic.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

# Initialize
KB_FILE_PATH = os.path.abspath(os.path.join("backend", "logic", "kb.metta"))
INFER_FILE_PATH = os.path.abspath(os.path.join("backend", "logic", "infer.metta"))

metta = MeTTa()
def reset_and_reload_metta():
    global metta
    metta = MeTTa()
    metta.run("!(register-module! ../backend)")
    
    try:
        with open(KB_FILE_PATH, 'r') as f:
            kb_content = f.read()
        metta.run(kb_content)
        print("Successfully loaded KB content from disk.")

        with open(INFER_FILE_PATH, 'r') as f:
            infer_content = f.read()
        metta.run(infer_content)
        print("Successfully loaded inference logic from disk.")
        
    except Exception as e:
        print(f"FATAL: Could not read or parse logic files on reset: {e}")

    print("MeTTa runner reloaded successfully.")

reset_and_reload_metta()

class AddFactsPayload(BaseModel):
    facts: List[str]

class RemoveFactPayload(BaseModel):
    fact: str


def execute_query(query: str) -> List[Dict[str, Any]]:
    print(f"Executing query: {query}")
    try:
        raw_result = metta.run(query)
        
        def atom_to_str(atom: Atom) -> Any:
            metatype = atom.get_metatype()
            if metatype == AtomKind.SYMBOL:
                return atom.get_name()
            elif metatype == AtomKind.EXPR:
                return [atom_to_str(sub_atom) for sub_atom in atom.get_children()]
            elif metatype == AtomKind.GROUNDED:
                try:
                    return repr(atom.get_object().content)
                except Exception:
                    return str(atom)
            else:
                return str(atom)

        flat_results = [
            atom_to_str(atom)
            for result_set in raw_result
            for atom in result_set
        ]
        
        unique_results = list(dict.fromkeys(flat_results))
        
        print(f"Query result: {unique_results}")
        return unique_results
    except Exception as e:
        print(f"Error executing query '{query}': {e}")
        return [{"error": str(e)}]

def parse_ancestor_paths(query: str) -> List[List[Dict[str, str]]]:
    print(f"Executing ancestor query: {query}")
    try:
        raw_result = metta.run(query)

        def atom_to_str(atom: Atom) -> Any:
            metatype = atom.get_metatype()
            if metatype == AtomKind.SYMBOL:
                return atom.get_name()
            elif metatype == AtomKind.EXPR:
                return [atom_to_str(sub_atom) for sub_atom in atom.get_children()]
            else:
                return str(atom)

        if not raw_result or not raw_result[0]:
            return []

        all_path_expressions = raw_result[0]
        
        formatted_paths = []
        for path_expr in all_path_expressions:
            path_list = atom_to_str(path_expr)

            if not path_list or not isinstance(path_list[0], list):
                path_list = [path_list]
            
            current_path = [{"name": ancestor[0], "sex": ancestor[1]} for ancestor in path_list]
            formatted_paths.append(list(reversed(current_path)))
        
        print(f"Formatted paths: {formatted_paths}")
        return formatted_paths

    except Exception as e:
        print(f"Error parsing ancestor paths for query '{query}': {e}")
        return [{"error": str(e)}]

def parse_descendant_paths(query: str) -> List[List[Dict[str, str]]]:
    print(f"Executing descendant query: {query}")
    try:
        raw_result = metta.run(query)

        def atom_to_str(atom: Atom) -> Any:
            metatype = atom.get_metatype()
            if metatype == AtomKind.SYMBOL:
                return atom.get_name()
            elif metatype == AtomKind.EXPR:
                return [atom_to_str(sub_atom) for sub_atom in atom.get_children()]
            else:
                return str(atom)

        if not raw_result or not raw_result[0]:
            return []

        all_path_expressions = raw_result[0]
        
        formatted_paths = []
        for path_expr in all_path_expressions:
            path_list = atom_to_str(path_expr)

            if not path_list or not isinstance(path_list[0], list):
                path_list = [path_list]
            
            current_path = [{"name": descendant[0], "sex": descendant[1]} for descendant in path_list]
            formatted_paths.append(list(reversed(current_path)))
        
        print(f"Formatted descendant paths: {formatted_paths}")
        return formatted_paths

    except Exception as e:
        print(f"Error parsing descendant paths for query '{query}': {e}")
        return [{"error": str(e)}]


@app.post("/api/add_facts", summary="Add Facts to Knowledge Base")
def add_facts(payload: AddFactsPayload):
    try:
        with open(KB_FILE_PATH, "r+") as f:
            existing_facts = {line.strip() for line in f}
            new_facts_added = 0
            
            f.seek(0, os.SEEK_END)
            if f.tell() > 0:
                f.seek(f.tell() - 1)
                if f.read(1) != '\n':
                    f.write('\n')

            for fact in payload.facts:
                if fact.strip() not in existing_facts:
                    f.write(f"{fact}\n")
                    new_facts_added += 1
        
        reset_and_reload_metta()
        
        if new_facts_added > 0:
            message = f"Successfully added {new_facts_added} new fact(s) and reloaded the knowledge base."
        else:
            message = "No new facts were added as they already exist in the knowledge base."
            
        print(message)
        return {"message": message}

    except Exception as e:
        print(f"Error adding facts: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.post("/api/remove_fact", summary="Remove Fact from Knowledge Base")
def remove_fact(payload: RemoveFactPayload):
    try:
        fact_to_remove = payload.fact.strip()
        lines_kept = []
        fact_found = False
        
        with open(KB_FILE_PATH, "r") as f:
            for line in f:
                if line.strip() == fact_to_remove:
                    fact_found = True
                else:
                    lines_kept.append(line)
        
        if not fact_found:
            return JSONResponse(status_code=404, content={"detail": "Fact not found in knowledge base."})

        with open(KB_FILE_PATH, "w") as f:
            f.writelines(lines_kept)
            
        reset_and_reload_metta()
        
        message = f"Successfully removed '{fact_to_remove}' and reloaded the knowledge base."
        print(message)
        return {"message": message}

    except Exception as e:
        print(f"Error removing fact: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})


@app.get("/api/children/{person}", summary="Get Children")
def get_children(person: str):
    query = f"!(children {person})"
    return execute_query(query)

@app.get("/api/siblings/{person}", summary="Get Siblings")
def get_siblings(person: str):
    query = f"!(sibilings {person})"
    return execute_query(query)

@app.get("/api/aunts-uncles/{person}", summary="Get Aunts and Uncles")
def get_aunts_uncles(person: str):
    query = f"!(aunts-uncles {person})"
    return execute_query(query)

@app.get("/api/aunts-or-uncles/{person}/{sex}", summary="Get Aunts or Uncles by Sex")
def get_aunts_or_uncles(person: str, sex: str):
    query = f"!(aunts_or_uncles {person} {sex})"
    return execute_query(query)

@app.get("/api/cousins/{person}", summary="Get Cousins")
def get_cousins(person: str):
    query = f"!(cousins {person})"
    return execute_query(query)

@app.get("/api/sex/{person}", summary="Get Sex")
def get_sex(person: str):
    query = f"!(get-sex {person})"
    return execute_query(query)

@app.get("/api/ancestors/{person}", summary="Get Ancestors")
def get_ancestors(person: str):
    query = f"!(ans {person} ())"
    return parse_ancestor_paths(query)

@app.get("/api/descendants/{person}", summary="Get Descendants")
def get_descendants(person: str):
    query = f"!(decendants {person} ())"
    return parse_descendant_paths(query)

@app.post("/api/query", summary="Execute Raw MeTTa Query")
def post_raw_query(query_body: Dict[str, str] = Body(..., example={"query": "!(cousins M)"})):
    query_str = query_body.get("query")
    if not query_str:
        return {"error": "Request body must contain a 'query' field."}
    return execute_query(query_str)

@app.get("/api/sisters-or-brothers/{person}/{sex}", summary="Get Sisters or Brothers")
def get_sisters_or_brothers(person: str, sex: str):
    query = f"!(sisters_or_brothers {person} {sex})"
    return execute_query(query)

AVAILABLE_TOOLS = {
    "get_ancestors": get_ancestors,
    "get_descendants": get_descendants,
    "get_children": get_children,
    "get_siblings": get_siblings,
    "get_aunts_or_uncles": get_aunts_or_uncles,
    "get_cousins": get_cousins,
    "get_sex": get_sex,
    "get_sisters_or_brothers": get_sisters_or_brothers,
}

TOOL_SCHEMAS = [
    {
        "name": "get_ancestors",
        "description": "Finds all ancestor paths for a given person. Use for questions about parents, grandparents, lineage, or family history.",
        "parameters": { "type": "object", "properties": { "person": { "type": "string", "description": "The name of the person."}}, "required": ["person"]}
    },
    {
        "name": "get_descendants",
        "description": "Finds all descendant paths for a given person. Use for questions about children, grandchildren, or offspring.",
        "parameters": { "type": "object", "properties": { "person": { "type": "string", "description": "The name of the person."}}, "required": ["person"]}
    },
    {
        "name": "get_children",
        "description": "Finds the immediate children of a given person.",
        "parameters": { "type": "object", "properties": { "person": { "type": "string", "description": "The name of the parent."}}, "required": ["person"]}
    },
    {
        "name": "get_siblings",
        "description": "Finds the siblings (brothers and sisters) of a given person.",
        "parameters": { "type": "object", "properties": { "person": { "type": "string", "description": "The name of the person."}}, "required": ["person"]}
    },
    {
        "name": "get_sisters_or_brothers",
        "description": "Finds only the sisters or only the brothers of a given person.",
        "parameters": { "type": "object", "properties": { "person": { "type": "string", "description": "The name of the person."}, "sex": { "type": "string", "description": "The desired sex of the siblings, either 'male' for brothers or 'female' for sisters."}}, "required": ["person", "sex"]}
    },
    {
        "name": "get_aunts_or_uncles",
        "description": "Finds the aunts or uncles of a given person, filtered by sex.",
        "parameters": { "type": "object", "properties": { "person": { "type": "string", "description": "The name of the person (e.g., the nephew or niece)."}, "sex": { "type": "string", "description": "The desired sex, either 'male' for uncles or 'female' for aunts."}}, "required": ["person", "sex"]}
    },
    {
        "name": "get_cousins",
        "description": "Finds all cousins of a given person.",
        "parameters": { "type": "object", "properties": { "person": { "type": "string", "description": "The name of the person."}}, "required": ["person"]}
    },
    {
        "name": "get_sex",
        "description": "Gets the recorded sex (gender) of a given person.",
        "parameters": { "type": "object", "properties": { "person": { "type": "string", "description": "The name of the person."}}, "required": ["person"]}
    }
]

def build_gemini_prompt(query: str) -> str:
    schemas_json = json.dumps(TOOL_SCHEMAS, indent=2)
    
    return f"""
You are an intelligent assistant for a family tree application. Your task is to analyze a user's query and determine which of the available tools should be called to answer it.

You must respond with a single, valid JSON object containing the 'tool_name' and the extracted 'arguments'. Do not add any other text or explanations.
Always capitalize the first letter of names in the arguments.
Here are the available tools and their schemas:
{schemas_json}

---
Here are some examples:

User Query: "Who are the ancestors of Kevin?"
Your Response:
{{
  "tool_name": "get_ancestors",
  "arguments": {{
    "person": "Kevin"
  }}
}}

User Query: "show me Diana's descendants"
Your Response:
{{
  "tool_name": "get_descendants",
  "arguments": {{
    "person": "Diana"
  }}
}}

User Query: "who are Charles's sisters"
Your Response:
{{
  "tool_name": "get_sisters_or_brothers",
  "arguments": {{
    "person": "Charles",
    "sex": "female"
  }}
}}
User Query: "who are Charles's brothers"
Your Response:
{{
  "tool_name": "get_sisters_or_brothers",
  "arguments": {{
    "person": "Charles",
    "sex": "male"
  }}
}}
User Query: "who are Charles's aunts"
Your Response:
{{
  "tool_name": "get_aunts_or_uncles",
  "arguments": {{
    "person": "Charles",
    "sex": "female"
  }}
}}
User Query: "who are Charles's uncles"
Your Response:
{{
  "tool_name": "get_aunts_or_uncles",
  "arguments": {{
    "person": "Charles",
    "sex": "male"
  }}
}}
---
Now, analyze the following user query and provide your response.

User Query: "{query}"
Your Response:
"""

@app.post("/api/natural_query")
async def natural_language_query(query_body: Dict[str, str] = Body(...)):
    try:
        query = query_body.get("query", "").strip()
        if not query:
            return JSONResponse(status_code=400, content={"error": "Query cannot be empty."})

        print(f"Received query: {query}")

        if query.startswith("!(") and query.endswith(")"):
            return {"message": f"Raw query result: {execute_query(query)}"}

        q_lower = query.lower()

        is_visualization_query = ('ancestor' in q_lower and ('visualize' in q_lower or 'show' in q_lower or 'tree' in q_lower)) or \
                               ('descendant' in q_lower and ('visualize' in q_lower or 'show' in q_lower or 'tree' in q_lower)) or \
                               ('visualize' in q_lower and ('family' in q_lower or 'tree' in q_lower))

        if is_visualization_query:
            if not genai:
                names = re.findall(r'\b([A-Z][a-z]+)\b', query)
                person = names[0] if names else None
            else:
                extraction_prompt = f"""
Extract the person's name from this family tree visualization query. Return only the name, nothing else.

Examples:
- "Visualize Charles ancestors" -> Charles
- "Show me Kevin's family tree" -> Kevin
- "Display Diana's descendants" -> Diana

Query: "{query}"
Person name:"""
                
                try:
                    model = genai.GenerativeModel(model_name='gemini-1.5-flash')
                    result = model.generate_content(extraction_prompt)
                    person = result.text.strip()
                    print(f"Gemini extracted person: {person}")
                except Exception as e:
                    print(f"Error extracting person with Gemini: {e}")
                    # Fallback to regex
                    names = re.findall(r'\b([A-Z][a-z]+)\b', query)
                    person = names[0] if names else None

            if not person:
                return {"message": "Could not identify a person's name. Please specify whose family tree you'd like to visualize."}

            print(f"Creating full family tree visualization for '{person}'")
            
            # Get both ancestors and descendants for complete tree visualization
            ancestors_data = get_ancestors(person)
            descendants_data = get_descendants(person)
            
            return {
                "type": "full_tree", 
                "person": person, 
                "ancestors": ancestors_data,
                "descendants": descendants_data
            }
        # --- End of visualization logic ---

        # Simple fallback parsing if Gemini is not available
        if not genai:
            print("Using fallback parsing (Gemini not available)")
            
            names = re.findall(r'\b([A-Z][a-z]+)\b', query)
            person = names[0] if names else None
            
            if not person:
                return {"message": "Could not identify a person's name. Please capitalize the name (e.g., 'Kevin', 'Laura')."}

            if 'ancestor' in q_lower:
                data = get_ancestors(person)
                return {"type": "ancestors", "person": person, "data": data}
            elif 'descendant' in q_lower:
                data = get_descendants(person)
                return {"type": "descendants", "person": person, "data": data}
            elif 'children' in q_lower or 'kids' in q_lower:
                data = get_children(person)
                return {"message": f"Children of {person}: {', '.join(data) if data else 'No children found'}"}
            elif 'sibling' in q_lower:
                data = get_siblings(person)
                return {"message": f"Siblings of {person}: {', '.join(data) if data else 'No siblings found'}"}
            elif 'cousin' in q_lower:
                data = get_cousins(person)
                return {"message": f"Cousins of {person}: {', '.join(data) if data else 'No cousins found'}"}
            elif 'sex' in q_lower or 'gender' in q_lower:
                data = get_sex(person)
                return {"message": f"{person} is {data[0] if data else 'unknown gender'}"}
            else:
                return {"message": "I can help you with questions about ancestors, descendants, children, siblings, cousins, or gender. Try asking something like 'Who are Kevin's children?' or 'Visualize Laura's family tree'."}

        # Use Gemini for intelligent parsing
        print("Using Gemini for query parsing")
        
        model = genai.GenerativeModel(model_name='gemini-1.5-flash')
        prompt = build_gemini_prompt(query)

        result = model.generate_content(prompt)
        response_text = result.text.strip()
        
        print(f"Gemini response: {response_text}")
        
        # Clean the response
        if response_text.startswith("```json"):
            response_text = response_text[7:-3].strip()
        elif response_text.startswith("```"):
            response_text = response_text[3:-3].strip()
        
        parsed_response = json.loads(response_text)
        
        tool_name = parsed_response.get("tool_name")
        tool_args = parsed_response.get("arguments", {})
        
        print(f"Gemini decided to call tool: {tool_name} with args: {tool_args}")

        if tool_name not in AVAILABLE_TOOLS:
            return {"message": f"I'm not sure how to help with that. Try asking about family relationships like children, siblings, ancestors, or descendants."}

        tool_function = AVAILABLE_TOOLS[tool_name]
        data = tool_function(**tool_args)
        person = tool_args.get("person", "")

        # For visualization queries (ancestors/descendants), return structured data
        if tool_name in ["get_ancestors", "get_descendants"]:
            return {
                "type": tool_name.replace("get_", ""),
                "person": person,
                "data": data
            }
        
        # For all other queries, use Gemini to generate conversational response
        conversational_response = generate_conversational_response(query, data, tool_name, person)
        return {"message": conversational_response}

    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return {"message": "I had trouble understanding that. Could you rephrase your question?"}
    except Exception as e:
        print(f"Error processing query: {e}")
        return {"message": f"Sorry, I encountered an error: {str(e)}"}


app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

try:
    api_key = os.getenv("GEMINI_API_KEY")
    print(f"API Key loaded: {api_key[:10]}..." if api_key else "No API key found")
    
    if not api_key:
        print("Warning: GEMINI_API_KEY environment variable not set. Gemini features will be disabled.")
        genai = None
    else:
        genai.configure(api_key=api_key)
        print("Gemini configured successfully")
except Exception as e:
    print(f"Error configuring Gemini: {e}")
    genai = None

def generate_conversational_response(query: str, raw_data: Any, tool_name: str, person: str) -> str:
    """
    Uses Gemini to generate a natural, conversational response based on the query and API results.
    """
    if not genai:
        return f"Found this information for {person}: {raw_data}"
    
    if not raw_data or (isinstance(raw_data, list) and len(raw_data) == 0):
        return f"I couldn't find any information about {person} for your query."
    
    if isinstance(raw_data, list) and len(raw_data) == 1 and isinstance(raw_data[0], dict) and 'error' in raw_data[0]:
        return f"Sorry, there was an error: {raw_data[0]['error']}"

    try:
        response_prompt = f"""
You are a helpful family tree assistant. Generate a natural, conversational response based on the user's query and the data returned from the family tree database.

User's original query: "{query}"
Function called: {tool_name}
Person queried: {person}
Raw data returned: {raw_data}

Important context about the data:
- get_children: Returns a list of children names (no gender info in the list itself)
- get_siblings: Returns a list of sibling names (no gender info in the list itself)
- get_sisters_or_brothers: Returns only sisters OR brothers based on the sex parameter
- get_aunts_or_uncles: Returns only aunts OR uncles based on the sex parameter
- get_cousins: Returns a list of cousin names
- get_sex: Returns the gender of a person

Generate a friendly, conversational response that:
1. Directly answers the user's question
2. Uses proper gender terminology when appropriate (sister/brother, aunt/uncle)
3. Includes the specific names found
4. Uses natural language (e.g., "Charles has two sisters: Anne and Diana" not "Charles sisters female Anne Diana")

Response:"""

        model = genai.GenerativeModel(model_name='gemini-1.5-flash')
        result = model.generate_content(response_prompt)
        
        return result.text.strip()
        
    except Exception as e:
        print(f"Error generating conversational response: {e}")
        # Fallback to simple response
        return f"I found this information about {person}: {', '.join(map(str, raw_data)) if isinstance(raw_data, list) else raw_data}"



# @app.post("/api/add_facts", summary="Add Facts to Knowledge Base")
# def add_facts(payload: AddFactsPayload):
#     """
#     Adds a list of new facts to the in-memory space and appends them to the kb.metta file.
#     This operation is fast and does not reload the entire knowledge base.
#     """
#     try:
#         space = metta.space()
#         tokenizer = metta.tokenizer()
#         new_facts_added_to_space = 0
#         new_facts_to_persist = []

#         for fact_str in payload.facts:
#             fact_str = fact_str.strip()
#             if not fact_str:
#                 continue
            
#             parsed_atom = SExprParser(fact_str).parse(tokenizer)
#             if parsed_atom is None:
#                 print(f"Warning: Could not parse fact '{fact_str}'")
#                 continue

#             # Check if the atom already exists in the space
#             if not space.query(parsed_atom).is_empty():
#                 continue

#             # If not, add it to the space and list for persistence
#             space.add_atom(parsed_atom)
#             new_facts_added_to_space += 1
#             new_facts_to_persist.append(fact_str)

#         # Persist the newly added facts to the file
#         if new_facts_to_persist:
#             with open(KB_FILE_PATH, "a") as f:
#                 f.write('\n' + '\n'.join(new_facts_to_persist) + '\n')
        
#         if new_facts_added_to_space > 0:
#             message = f"Successfully added {new_facts_added_to_space} new fact(s) to the knowledge base."
#         else:
#             message = "No new facts were added as they already exist in the knowledge base."
            
#         print(message)
#         return {"message": message}

#     except Exception as e:
#         print(f"Error adding facts: {e}")
#         return JSONResponse(status_code=500, content={"detail": str(e)})

# @app.post("/api/remove_fact", summary="Remove Fact from Knowledge Base")
# def remove_fact(payload: RemoveFactPayload):
#     """
#     Removes a specific fact from the in-memory space and the kb.metta file.
#     This operation is fast and does not reload the entire knowledge base.
#     """
#     try:
#         fact_to_remove_str = payload.fact.strip()
#         parsed_atom = SExprParser(fact_to_remove_str).parse(metta.tokenizer())
        
#         if parsed_atom is None:
#             return JSONResponse(status_code=400, content={"detail": "Could not parse fact to remove."})

#         # Remove the atom from the in-memory space
#         if not metta.space().remove_atom(parsed_atom):
#             return JSONResponse(status_code=404, content={"detail": "Fact not found in the in-memory knowledge base."})

#         # If successful, also remove it from the file
#         lines_kept = []
#         with open(KB_FILE_PATH, "r") as f:
#             for line in f:
#                 if line.strip() != fact_to_remove_str:
#                     lines_kept.append(line)
        
#         with open(KB_FILE_PATH, "w") as f:
#             f.writelines(lines_kept)
            
#         message = f"Successfully removed '{fact_to_remove_str}' from the knowledge base."
#         print(message)
#         return {"message": message}

#     except Exception as e:
#         print(f"Error removing fact: {e}")
#         return JSONResponse(status_code=500, content={"detail": str(e)})