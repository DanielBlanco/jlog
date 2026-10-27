# Linux resource measurements in Docker

This image installs the exact Roc compiler pin and GNU time, then runs jlog as
UID 1000. It mounts application sources read-only and stores build outputs,
caches, generated fixtures, and results on the container's Linux filesystem.
The compiler archive and Debian base manifest are pinned by SHA-256 in
[Dockerfile](Dockerfile). Apt tooling versions are recorded with the measurements;
future image rebuilds can receive Debian security updates.

On Apple Silicon, `linux/arm64` uses the matching Linux guest architecture. It
does **not** satisfy native Linux x86-64 release verification. An amd64 image on
an ARM64 engine would use cross-architecture execution; label such observations
as emulated and do not use them as native performance evidence. The Dockerfile
contains both pinned compiler assets, but only ARM64 was exercised here.

From the repository root:

```sh
docker build --platform linux/arm64 --tag jlog-m4-linux-arm64 tests/docker
docker run --detach --init --platform linux/arm64 --name jlog-m4-linux-arm64 \
  --mount "type=bind,src=$PWD,dst=/src,readonly" jlog-m4-linux-arm64
docker exec jlog-m4-linux-arm64 sh tests/docker/verify.sh
```

[verify.sh](verify.sh) checks the compiler version, formatting and types, runs
273 pure checks and 63 ordinary executable methods against both dev and speed
builds, and checks timing-parser units. Permission fixtures run unprivileged.
The optimized ELF is `/work/jlog-speed`; the macOS `dist/jlog` is untouched.

The separate strict descriptor suite is a release gate, currently failing on
both measured OSes. Run it explicitly and retain its nonzero status:

```sh
docker exec --env JLOG_BIN=/work/jlog-speed jlog-m4-linux-arm64 \
  python3 -m unittest discover -s tests -p test_io_contract.py -v
```

Before measuring, record the image ID, engine/guest architectures, virtual CPU
and memory limits, physical-host identity, and whether execution is emulated.
`--environment` accepts a JSON file containing that provenance. Sources remain
under `/src`; `/work` and `/tmp` are inside the Linux guest, so input/output does
not cross the source bind mount during timing.

Once dependencies have been resolved, disconnect the container network and
validate the native timing tool:

```sh
docker network disconnect bridge jlog-m4-linux-arm64
docker inspect jlog-m4-linux-arm64 --format '{{json .NetworkSettings.Networks}}'
docker exec jlog-m4-linux-arm64 /usr/bin/time -v /usr/bin/true
docker exec jlog-m4-linux-arm64 python3 tests/measure_resources.py \
  --binary /work/jlog-speed --work-dir /work/smoke \
  --sizes 100 1000 --tail-sizes 0 1 8 --long-lines 1024 4096
docker exec jlog-m4-linux-arm64 python3 tests/measure_resources.py \
  --binary /work/jlog-speed --work-dir /work/full
```

The default matrix contains 70 sequential cases and needs about 3 GiB of disk
space. GNU time reports RSS in KiB; the driver converts it to bytes, matching the
JSON unit used on macOS. These values measure the CLI process, excluding the
driver, Docker VM, host, and filesystem page cache. Output hashes/statuses and
unchanged input/binary hashes are verified separately from timing.

Copy the compact report out before stopping this task's container:

```sh
docker cp jlog-m4-linux-arm64:/work/full/results.json /tmp/jlog-linux-resources.json
docker stop jlog-m4-linux-arm64
```

The stopped container retains raw timing/diagnostic artifacts for review. Avoid
copying generated gigabyte fixtures into the repository. The measured ARM64 run
is recorded in the project's `docs/measurements/` directory; it is supplemental
Linux evidence. Required native x86-64 execution is now recorded separately in
the [CI report](../../docs/plans/m4-03-native-ci.md) and
[resource measurements](../../docs/measurements/m4-02-linux-x86_64-ci.md).
