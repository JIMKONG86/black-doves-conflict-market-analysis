Requirements:

Inherit from Observation.
Use super() for observation_date, source, and verification_status.
Store the remaining five values as its own attributes.
Do not add it to main.py yet.

Use the reported_ prefix deliberately: these figures represent claims from a source, not automatically verified facts.

Also remember for later:

0    → confirmed zero
None → unknown or not reported

Write the class from memory, save it, and check it with:

python -m py_compile src/models/observations.py

Then send me the result for QA.