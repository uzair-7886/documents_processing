from extraction.rules.predict_next_date_of_inspection import predict_next_date_of_inspection
from extraction.rules.predict_client_name import predict_client_name
from extraction.rules.predict_certificate_number import predict_certificate_number
from extraction.rules.predict_job_number import predict_job_number
from extraction.rules.predict_course_name import predict_course_name
from extraction.rules.predict_company_name import predict_company_name
from extraction.rules.predict_course_start_date import predict_course_start_date
from extraction.rules.predict_course_validity_duration import predict_course_validity_duration
from extraction.rules.predict_company_id import predict_company_id
from extraction.rules.predict_emirates_id import predict_emirates_id
from extraction.rules.predict_type_of_inspection import predict_type_of_inspection
from extraction.rules.predict_inspection_description import predict_inspection_description
from extraction.rules.predict_date_of_inspection import predict_date_of_inspection
field_to_predictor={
    "next_date_of_inspection": predict_next_date_of_inspection,
    "client_name": predict_client_name,
    "certificate_number": predict_certificate_number,
    "job_number": predict_job_number,
    "course_name": predict_course_name,
    "company_name": predict_company_name,
    "course_start_date":predict_course_start_date,
    "course_validity_duration":predict_course_validity_duration,
    "company_id": predict_company_id,
    "emirates_id": predict_emirates_id,
    "type_of_inspection": predict_type_of_inspection,
    "inspection_description": predict_inspection_description,
    "date_of_inspection": predict_date_of_inspection
}