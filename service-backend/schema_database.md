Users (table `public.users`, liée à `auth.users`) :
user_id,
email,
fullname,
(authentication : Supabase Auth — pas de colonne password ici),
created_at,
updated_at.


Clients : 
client_id,
user_id,
client_name,
created_at,
updated_at.


Files :
file_id,
client_id,
original_filename,
s3_raw_path,
s3_silver_path,
silver_content (JSONB),
file_format (pdf, jpg...),
type (attestation, kbis...)
processing_status (pending, error, done)
created_at,
updated_at.


Conformity_reports :
report_id
client_id,
gold_content (JSONB),
s3_gold_path,
silver_content (JSONB),
processing_status (pending, error, done)
created_at,
updated_at.
