# Supabase configuration

from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://xaxgkufwhemjoofcvtri.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhheGdrdWZ3aGVtam9vZmN2dHJpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTEwMDA5MjIsImV4cCI6MjA2NjU3NjkyMn0.LZQij2Go9v0gC-302BsqfoLPWdU_g3SF_P6JLitbLTk")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)