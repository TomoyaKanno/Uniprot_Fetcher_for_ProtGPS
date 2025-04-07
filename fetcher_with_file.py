import streamlit as st
import requests
import re
import html

def fetch_uniprot_data(accession):
    url = f"https://rest.uniprot.org/uniprotkb/{accession}?fields=accession%2Cprotein_name%2C%20sequence%2C%20organism_name%2C%20gene_primary"
    response = requests.get(url)
    return response.json()

def format_sequence_entry(data, mutation=None):
    protein_name = data["proteinDescription"]["recommendedName"]["fullName"]["value"]
    organism = data["organism"]["scientificName"]
    
    # Add mutation information or [WT] right after UniProt ID
    mutation_info = f"[{mutation}]" if mutation else "[WT]"
    comment = f"# UniProt {data['primaryAccession']} {mutation_info} - {protein_name} ({organism})"
    
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

def format_fasta_entry(data, sequence, mutation_code=None):
    """Format a sequence entry in FASTA format
    
    Creates a FASTA-formatted entry with the header containing the gene name,
    organism, UniProt ID, and mutation status (if applicable), followed by
    the sequence with standard line breaks every 60 characters.
    
    Parameters:
    -----------
    data : dict
        UniProt data dictionary containing protein information
    sequence : str
        Protein sequence (original or mutated)
    mutation_code : str, optional
        Mutation code if the sequence is mutated
        
    Returns:
    --------
    str
        FASTA formatted entry with header and sequence
    """
    # Extract information for FASTA header
    gene = data["genes"][0]["geneName"]["value"] if "genes" in data and data["genes"] else "Unknown"
    organism = data["organism"]["commonName"] if "commonName" in data["organism"] else data["organism"]["scientificName"]
    uniprot_id = data["primaryAccession"]
    mutation_info = f"[{mutation_code}]" if mutation_code else "[WT]"
    
    # Create FASTA header: >gene|organism|uniprot_id|mutation_status
    fasta_header = f">{gene}|{organism}|{uniprot_id}|{mutation_info}"
    
    # Format sequence with line breaks every 60 characters (standard FASTA format)
    formatted_sequence = ""
    for i in range(0, len(sequence), 60):
        formatted_sequence += sequence[i:i+60] + "\n"
    
    return f"{fasta_header}\n{formatted_sequence.strip()}"

# Initialize session state with default values
default_state = {
    'sequences': [],           # List to store collected sequences
    'labels': [],              # List to store reordered headers
    'current_data': None,      # Current UniProt data
    'mutated_sequence': None,  # Current mutated sequence
    'mutation_code': None,     # Current mutation code
    'fasta_sequences': [],     # List to store FASTA formatted sequences
}

for key, value in default_state.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Streamlit interface
st.title("UniProt Sequence Collector")

# Input section with two side-by-side input boxes
col1, col2 = st.columns(2)
with col1:
    accession = st.text_input("Enter UniProt Accession ID", value="Q9Y5B6")
with col2:
    mutation_code = st.text_input("Enter mutation (Optional)", placeholder="e.g., P30R or P30TER")

# Fetch and Format button - using full width
if st.button("Fetch and Format"):
    data = fetch_uniprot_data(accession)
    st.session_state.current_data = data
    
    # Get the original sequence data
    original_comment, original_sequence = format_sequence_entry(data)
    
    # If mutation is provided, apply it
    if mutation_code:
        st.session_state.mutation_code = mutation_code
        mutated_sequence, error = apply_mutation(original_sequence, mutation_code)
        
        if error:
            st.error(error)
            # Show the original sequence if there's an error
            st.code(f'{original_comment}\n"{original_sequence}"', language="python")
            st.session_state.mutated_sequence = None
        else:
            st.session_state.mutated_sequence = mutated_sequence
            
            # Extract mutation position and check if it's a termination
            pattern = r"([A-Z])(\d+)([A-Z]{1,3})"
            match = re.match(pattern, mutation_code)
            orig_aa, position, new_aa = match.groups()
            is_termination = (new_aa == "TER")
            pos_index = int(position) - 1  # 0-based index
            
            # Create a better mutation preview
            st.subheader("Mutation Preview")
            
            # Create containers for side-by-side display
            preview_col1, preview_col2 = st.columns(2)
            
            # Original sequence display with highlight
            with preview_col1:
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
            with preview_col2:
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
            comment_with_mutation, _ = format_sequence_entry(data, mutation_code)
            st.code(f'{comment_with_mutation}\n"{mutated_sequence}"', language="python")
    else:
        # If no mutation is provided, show the original sequence
        st.session_state.mutation_code = None
        st.session_state.mutated_sequence = None
        st.code(f'{original_comment}\n"{original_sequence}"', language="python")

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
        
        # Create reordered label with organism first, protein name second, and mutation/WT last
        data = st.session_state.current_data
        protein_name = data["proteinDescription"]["recommendedName"]["fullName"]["value"]
        organism = data["organism"]["commonName"]
        gene = data["genes"][0]["geneName"]["value"]
            
        mutation_info = f"[{st.session_state.mutation_code}]" if st.session_state.mutation_code else "[WT]"
        reordered_label = f"{organism}, {gene}, {mutation_info}"
        
        # Create FASTA formatted entry (silently build as requested)
        fasta_entry = format_fasta_entry(
            data, 
            sequence, 
            st.session_state.mutation_code
        )
        
        if formatted_entry not in st.session_state.sequences:
            st.session_state.sequences.append(formatted_entry)
            st.session_state.labels.append(reordered_label)
            st.session_state.fasta_sequences.append(fasta_entry)
            st.success("Sequence added to list!")
        else:
            st.warning("This sequence is already in the list!")
    else:
        st.warning("Please fetch a sequence first!")

# Display the collected sequences and labels side by side
if st.session_state.sequences:
    st.subheader("Collected Data")
    
    # Create two columns for side-by-side display
    col1, col2 = st.columns(2)
    
    # First column: Sequences
    with col1:
        st.markdown("### Sequences")
        formatted_sequences = "sequences = [\n    " + ",\n    ".join(st.session_state.sequences) + "\n]"
        st.code(formatted_sequences, language="python")
    
    # Second column: Labels
    with col2:
        st.markdown("### Labels")
        formatted_labels = "labels = [\n    " + ",\n    ".join([f'"{label}"' for label in st.session_state.labels]) + "\n]"
        st.code(formatted_labels, language="python")
    
    # Add export controls
    st.markdown("### Export Options")
    export_col1, export_col2 = st.columns(2)
    
    with export_col1:
        # Clear Lists button
        if st.button("Clear Lists"):
            st.session_state.sequences = []
            st.session_state.labels = []
            st.session_state.fasta_sequences = []
            st.success("Lists cleared!")
    
    with export_col2:
        # Export to FASTA button
        if st.button("Export to FASTA"):
            # Join all FASTA entries
            fasta_content = "\n".join(st.session_state.fasta_sequences)
            
            # Create download button
            st.download_button(
                label="Download FASTA File",
                data=fasta_content,
                file_name="sequences.fasta",
                mime="text/plain",
            )