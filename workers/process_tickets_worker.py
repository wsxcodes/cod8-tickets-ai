import logging
import os
import sys

import pandas as pd
from openai import OpenAI

# Add the parent directory to sys.path
current_dir = os.path.dirname(__file__)
parent_dir = os.path.join(current_dir, '..')
sys.path.append(os.path.abspath(parent_dir))

from backend import config  # NoQA
from backend.interfaces.azure_ai_search import AzureSearchClient  # NoQA

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

INDEX_NAME = "ticket_index"

azure_client = AzureSearchClient(
    service_url=config.AZURE_AI_SEARCH_SERVICE,
    index_name=INDEX_NAME,
    api_key=config.AZURE_AI_SEARCH_API_KEY,
    vector_field="vector"
)

openai_client = OpenAI(api_key=config.CHATGPT_KEY)


def process_ticket_csv(filename):
    """
    Reads a CSV file containing ticket data, generates a new sequential primary 'id',
    and stores the original ticket id from 'TicketNbr' as 'ticket_id'.
    Also adds a placeholder 'vector' field.
    """
    # Define the columns to extract.
    # 'TicketNbr' is only used to capture the actual ticket id.
    required_columns = [
        "TicketNbr",
        "Summary",
        "Status_Description",
        "Status",
        "Company_Name",
        "Date_Entered",
        "Discussion",
        "Type",
        "ServiceLocation",
        "Priority",
        "Source",
        "Team"
    ]
    df = pd.read_csv(filename, dtype={"TicketNbr": str})
    df.rename(columns={"Textbox112": "Discussion"}, inplace=True)

    missing_columns = set(required_columns) - set(df.columns)
    if missing_columns:
        logger.info(f"Warning: Missing columns in CSV: {missing_columns}")

    # Keep only available columns from the required list.
    df_subset = df[[col for col in required_columns if col in df.columns]].copy()

    # Capture the actual ticket id into a new column 'ticket_id' and drop the original.
    if "TicketNbr" in df_subset.columns:
        df_subset["ticket_id"] = df_subset["TicketNbr"]
        df_subset.drop(columns=["TicketNbr"], inplace=True)
    else:
        df_subset["ticket_id"] = ""

    # Insert a new sequential primary id column as string (starting from 1)
    df_subset.insert(0, "id", [str(i) for i in range(1, len(df_subset) + 1)])

    # Add a placeholder for the vector.
    df_subset["vector"] = None

    # Rename the relevant columns to lowercase.
    df_subset.rename(
        columns={
            "Company_Name": "company_name",
            "Date_Entered": "date_entered",
            "Type": "type",
            "Priority": "priority",
            "Source": "source",
            "Team": "team",
            "Discussion": "discussion"
        },
        inplace=True
        )

    # Rename the "Summary" column to "title".
    df_subset.rename(columns={"Summary": "title"}, inplace=True)

    # Define final column order as per the updated schema.
    final_order = [
        "id",
        "ticket_id",
        "vector",
        "title",
        "company_name",
        "date_entered",
        "discussion",
        "type",
        "priority",
        "source",
        "team"
    ]
    df_final = df_subset[[col for col in final_order if col in df_subset.columns]]

    # Group rows by ticket_id to accumulate discussion from multiple records.
    df_grouped = df_final.groupby("ticket_id", as_index=False).agg({
        "title": "first",
        "company_name": "first",
        "date_entered": "first",
        "discussion": lambda x: " ".join(x.dropna().astype(str)),
        "type": "first",
        "priority": "first",
        "source": "first",
        "team": "first",
        "vector": "first"
    })
    df_grouped.sort_values(by="ticket_id", ascending=False, inplace=True)
    # Recalculate sequential primary id for grouped records.
    df_grouped.insert(0, "id", [str(i) for i in range(1, len(df_grouped) + 1)])
    df_grouped = df_grouped[final_order]
    return df_grouped


def vectorize_ticket(ticket: pd.Series) -> pd.Series:
    """
    Vectorizes the ticket's title field using OpenAI embeddings and stores the result in 'vector'.
    """
    logger.info(f"Vectorizing ticket {ticket['id']} (actual ticket id: {ticket.get('ticket_id', 'N/A')})")
    text_to_embed = ticket.get("title", "")
    if not text_to_embed:
        logger.info(f"No title for ticket {ticket['id']}. Skipping vectorization.")
        return ticket

    try:
        response = openai_client.embeddings.create(
            input=text_to_embed,
            model=config.OPENAI_EMBEDDING_MODEL
        )
        embedding_vector = response.data[0].embedding
        ticket["vector"] = embedding_vector
        logger.info(f"Ticket {ticket['id']} vectorized successfully.")
    except Exception as e:
        logger.info(f"Error vectorizing ticket {ticket['id']}: {e}")
    return ticket


def upload_ticket(ticket: pd.Series):
    """
    Uploads the ticket document to Azure Search.
    """
    try:
        doc_id = str(ticket["id"])
        # Prepare metadata excluding the vector field.
        metadata = ticket.drop("vector").to_dict() if "vector" in ticket else ticket.to_dict()
        azure_client.upload_document(
            doc_id=doc_id,
            embedding=ticket["vector"],
            metadata=metadata
        )
        logger.info(f"Uploaded ticket {doc_id}")
    except Exception as e:
        logger.info(f"Error uploading ticket {ticket.get('id', 'unknown')}: {e}")


if __name__ == "__main__":
    filepath = "data/Bank_Design_Equipment_FY2024.csv"
    tickets_df = process_ticket_csv(filepath)

    # Debug: Log unique primary ids and actual ticket ids.
    unique_ids = tickets_df['id'].unique()
    unique_ticket_ids = tickets_df['ticket_id'].unique()
    logger.info(f"Unique primary ids: {unique_ids}")
    logger.info(f"Unique actual ticket ids: {unique_ticket_ids}")

    logger.info("Processed ticket data:")
    logger.info(tickets_df.head())

    for idx, ticket in tickets_df.iterrows():
        logger.info(f"Processing row {idx} with primary id: {ticket['id']} and actual ticket id: {ticket['ticket_id']}")

        print(ticket)
        logger.info(f"Discussion length: {len(ticket['discussion']) if isinstance(ticket['discussion'], str) else 'N/A'}")
        input("Hit enter to continue..")

        # XXX TODO
        # ticket = vectorize_ticket(ticket)
        # upload_ticket(ticket)
