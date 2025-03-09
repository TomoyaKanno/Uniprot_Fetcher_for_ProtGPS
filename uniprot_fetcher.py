import streamlit as st
import requests
import re
import html

def fetch_uniprot_data(accession):
    url = f"https://rest.uniprot.org/uniprotkb/{accession}?fields=accession%2Cprotein_name%2C%20sequence%2C%20organism_name"
    response = requests.get(url)
    return response.json()

def format_sequence_entry(data, mutation=None):
    protein_name = data["proteinDescription"]["recommendedName"]["fullName"]["value"]
    organism = data["organism"]["scientificName"]
    
    # Add mutation information to the comment if a mutation was applied
    mutation_info = f" [{mutation}]" if mutation else ""
    comment = f"# UniProt {data['primaryAccession']} - {protein_name} ({organism}){mutation_info}"
    
    sequence = data["sequence"]["value"]
    return comment, sequence

def apply_mutation(sequence, mutation_code):
    """Apply a mutation to a protein sequence"""
    # Regular expression to match mutation codes like P30R or P30TER
    pattern = r"([A-Z])(\d+)([A-Z]{1,3})"
    match = re.match(pattern, mutation_code)
    
    if not match:
        return None, "Invalid mutation format. Use format like 'P30R' or 'P30TER'."
    
    orig_aa, position, new_aa = match.groups()
    position = int(position) - 1  # Convert to 0-based index
    
    # Validate position
    if position < 0 or position >= len(sequence):
        return None, f"Position out of range. Sequence length is {len(sequence)}."
    
    # Validate original amino acid
    if sequence[position] != orig_aa:
        return None, f"Original amino acid mismatch. Expected {orig_aa} but found {sequence[position]} at position {int(position) + 1}."
    
    # Apply mutation
    if new_aa == "TER":
        # Termination - truncate the sequence
        mutated_sequence = sequence[:position]
    else:
        # Amino acid substitution
        mutated_sequence = sequence[:position] + new_aa + sequence[position + 1:]
    
    return mutated_sequence, None

# Initialize session state with default values
default_state = {
    'sequences': [],           # List to store collected sequences
    'current_data': None,      # Current UniProt data
    'mutated_sequence': None,  # Current mutated sequence
    'mutation_code': None,     # Current mutation code
    'show_mutation_input': False  # Whether to show mutation input field
}

for key, value in default_state.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Streamlit interface
st.title("UniProt Sequence Collector")

# Input section
accession = st.text_input("Enter UniProt Accession ID", value="Q9Y5B6")

# Fetch and Format button - using full width
if st.button("Fetch and Format"):
    data = fetch_uniprot_data(accession)
    st.session_state.current_data = data
    st.session_state.mutated_sequence = None
    st.session_state.mutation_code = None
    st.session_state.show_mutation_input = False
    comment, sequence = format_sequence_entry(data)
    st.code(f'{comment}\n"{sequence}"', language="python")

# Add mutation button and related functionalities
if st.session_state.current_data is not None:
    if st.button("Add Mutation"):
        st.session_state.show_mutation_input = True
    
    if st.session_state.show_mutation_input:
        mutation_code = st.text_input("Enter mutation (e.g., P30R or P30TER)")
        
        if mutation_code:
            comment, original_sequence = format_sequence_entry(st.session_state.current_data)
            
            # Apply the mutation
            mutated_sequence, error = apply_mutation(original_sequence, mutation_code)
            
            if error:
                st.error(error)
            else:
                st.session_state.mutated_sequence = mutated_sequence
                st.session_state.mutation_code = mutation_code
                
                # Display original and mutated sequences
                st.subheader("Original Sequence")
                st.code(f'{comment}\n"{original_sequence}"', language="python")
                
                # Extract mutation position and check if it's a termination
                pattern = r"([A-Z])(\d+)([A-Z]{1,3})"
                match = re.match(pattern, mutation_code)
                orig_aa, position, new_aa = match.groups()
                is_termination = (new_aa == "TER")
                pos_index = int(position) - 1  # 0-based index
                
                # Create a better mutation preview
                st.subheader("Mutation Preview")
                
                # Create containers for side-by-side display
                col1, col2 = st.columns(2)
                
                # Original sequence display with highlight
                with col1:
                    st.markdown("**Original:**")
                    st.text(f"Position: {position}")
                    
                    # Format sequence with highlighted position
                    formatted_orig = (
                        f'<div style="font-family:monospace; max-width:100%; overflow-x:auto; '
                        f'border:1px solid #ccc; padding:8px; border-radius:4px;">'
                        f'<div style="word-wrap:break-word; white-space:pre-wrap; width:100%;">'
                        f'{html.escape(original_sequence[:pos_index])}'
                        f'<span style="background-color:#ff6b6b;color:white;padding:0 2px;">{html.escape(original_sequence[pos_index])}</span>'
                        f'{html.escape(original_sequence[pos_index + 1:])}'
                        f'</div></div>'
                    )
                    st.markdown(formatted_orig, unsafe_allow_html=True)
                
                # Mutated sequence display with highlight
                with col2:
                    st.markdown("**Mutated:**")
                    st.text(f"Mutation: {mutation_code}")
                    
                    if is_termination:
                        # For termination, show truncated sequence with marker
                        formatted_mut = (
                            f'<div style="font-family:monospace; max-width:100%; overflow-x:auto; '
                            f'border:1px solid #ccc; padding:8px; border-radius:4px;">'
                            f'<div style="word-wrap:break-word; white-space:pre-wrap; width:100%;">'
                            f'{html.escape(mutated_sequence)}'
                            f'<span style="background-color:#ff6b6b;color:white;padding:0 2px;">■</span>'
                            f'</div></div>'
                        )
                    else:
                        # Format sequence with highlighted mutation
                        formatted_mut = (
                            f'<div style="font-family:monospace; max-width:100%; overflow-x:auto; '
                            f'border:1px solid #ccc; padding:8px; border-radius:4px;">'
                            f'<div style="word-wrap:break-word; white-space:pre-wrap; width:100%;">'
                            f'{html.escape(mutated_sequence[:pos_index])}'
                            f'<span style="background-color:#ff6b6b;color:white;padding:0 2px;">{html.escape(mutated_sequence[pos_index])}</span>'
                            f'{html.escape(mutated_sequence[pos_index + 1:])}'
                            f'</div></div>'
                        )
                    st.markdown(formatted_mut, unsafe_allow_html=True)
                
                # Show full mutated sequence
                st.subheader("Mutated Sequence")
                comment_with_mutation, _ = format_sequence_entry(st.session_state.current_data, mutation_code)
                st.code(f'{comment_with_mutation}\n"{mutated_sequence}"', language="python")

# Add to List button
if st.button("Add to List"):
    if st.session_state.current_data is not None:
        # Determine if we're adding the original or mutated sequence
        if st.session_state.mutated_sequence is not None:
            comment, _ = format_sequence_entry(st.session_state.current_data, st.session_state.mutation_code)
            sequence = st.session_state.mutated_sequence
        else:
            comment, sequence = format_sequence_entry(st.session_state.current_data)
        
        formatted_entry = f'{comment}\n"{sequence}"'
        
        if formatted_entry not in st.session_state.sequences:
            st.session_state.sequences.append(formatted_entry)
            st.success("Sequence added to list!")
        else:
            st.warning("This sequence is already in the list!")
    else:
        st.warning("Please fetch a sequence first!")

# Display the collected sequences
if st.session_state.sequences:
    st.subheader("Collected Sequences")
    formatted_list = "sequences = [\n    " + ",\n    ".join(st.session_state.sequences) + "\n]"
    st.code(formatted_list, language="python")
    
    # Add a clear list button
    if st.button("Clear List"):
        st.session_state.sequences = []
        st.success("List cleared!")