# Testing the availability of various MySQL packages/tarballs on the main site

## PS (full PS version needed)
```
docker run --env PS_VER_FULL=8.0.34-26.1 --rm -v `pwd`:/tmp -w /tmp python bash -c "pip3 install requests pytest setuptools && env && pytest -s --junitxml=junit.xml test_ps.py"
```
## PDPS (full PS, PXB, ORCH  versions needed)
```
docker run --env PS_VER_FULL=8.0.34-26.1 --env PXB_VER_FULL=8.0.34-29.1 --env ORCH_VER_FULL=3.2.6-10 --env PT_VER=3.5.4 --env PROXYSQL_VER=2.5.5 --rm -v `pwd`:/tmp -w /tmp python bash -c "pip3 install requests pytest setuptools && env && pytest -s --junitxml=junit.xml test_pdps.py"
```
## PXC (full PXC version needed)
```
docker run --env PXC_VER_FULL=8.0.34-26.1 --rm -v `pwd`:/tmp -w /tmp python bash -c "pip3 install requests pytest setuptools && env && pytest -s --junitxml=junit.xml test_pxc.py"

docker run --env PXC_VER_FULL=5.7.43-31.65.1 --rm -v `pwd`:/tmp -w /tmp python bash -c "pip3 install requests pytest setuptools && env && pytest -s --junitxml=junit.xml test_pxc.py"
```
## PDPXC (full PXC, PXB, ORCH  versions needed)
```
docker run --env PXC_VER_FULL=8.0.34-26.1 --env PXB_VER_FULL=8.0.34-29.1 --env PT_VER=3.5.4 --env ORCH_VER_FULL=3.2.6-10 --env PROXYSQL_VER=2.5.5 --env HAPROXY_VER=2.8.1 --env REPL_MAN_VER=1.0 --rm -v `pwd`:/tmp -w /tmp python bash -c "pip3 install requests pytest setuptools && env && pytest -s --junitxml=junit.xml test_pdpxc.py"
```
## PXB (full PXB version needed)
```
docker run --env PXB_VER_FULL=8.0.34-29.1 --rm -v `pwd`:/tmp -w /tmp python bash -c "pip3 install requests pytest setuptools && env && pytest -s --junitxml=junit.xml test_pxb.py"

docker run --env PXB_VER_FULL=2.4.28-1 --rm -v `pwd`:/tmp -w /tmp python bash -c "pip3 install requests pytest setuptools && env && pytest -s --junitxml=junit.xml test_pxb.py"
```

