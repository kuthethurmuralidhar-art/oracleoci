CREATE OR REPLACE FUNCTION GET_MATCHED_CANDIDATES (
    p_keyword IN VARCHAR2,
    p_location IN VARCHAR2
) RETURN SYS_REFCURSOR IS
    c_results SYS_REFCURSOR;
BEGIN
    OPEN c_results FOR
        SELECT id, name, email, experience_years, location, skills_matrix, resume_blob
        FROM skills
        WHERE (p_location IS NULL OR INSTR(LOWER(p_location), LOWER(TRIM(location))) > 0)
          AND (p_keyword IS NULL OR LOWER(skills_matrix) LIKE '%' || LOWER(TRIM(p_keyword)) || '%');
          
    RETURN c_results;
END;
/

SELECT object_name, status 
FROM user_objects 
WHERE object_name = 'GET_MATCHED_CANDIDATES';