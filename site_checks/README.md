# Testing the availability of various packages/tarballs on the main site

## PS (full PS version needed) 
```
docker run --env PS_VER_FULL=8.0.34-26.1 --rm -v `pwd`:/tmp -w /tmp python bash -c "pip3 install requests pytest setuptools && env && pytest -s --junitxml=junit.xml test_ps.py"
```