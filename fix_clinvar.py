import re
lines = open('varidex/io/loaders/clinvar.py').readlines()
content = ''.join(lines)

# Replace broken except block
fixed = re.sub(
    r'except Exception as e:.*?(?=\n[A-Za-z])',
    'except Exception as e:\n        logger.exception(e)\n        raise',
    content,
    flags=re.DOTALL
)

with open('varidex/io/loaders/clinvar.py', 'w') as f:
    f.write(fixed)
print("✅ Fixed clinvar.py indentation")
