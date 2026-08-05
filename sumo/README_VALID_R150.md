# StudyArea valid RSU configuration, R=150 m

This package fixes the previous oversized RSU coverage circle.

## Main changes
- RSU center: x=80, y=36
- RSU radius: R=150 m
- The previous R=300 m was too large because it covered almost the entire corridor.
- `time-to-teleport` is set to 300 s to avoid indefinitely stalled vehicles.

## Run

```bash
conda activate sumo-env
export SUMO_HOME=$CONDA_PREFIX

sumo-gui -c studyarea_test_with_decal.sumocfg --start --delay 100
sumo -c studyarea_test.sumocfg

cp StudyAreNetwork.net.xml bpu.net.xml
bash run_studyarea_bpu.sh

rm -f fcd.xml
ln -s studyarea_fcd.xml fcd.xml
python cross_validate_studyarea.py fcd.xml
```

## Main output
- `studyarea_fcd.xml`
- `contact_times.csv`
- `delivery_vs_n.csv`
- `fig_delivery_sumo.png`
- terminal output from `cross_validate_studyarea.py`
