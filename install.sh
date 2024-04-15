cd $WORKROOT/memorytools/memorytools
mkdir -p $WORKROOT/pyvlttoo/src/vlttoo/memorytools
touch  $WORKROOT/pyvlttoo/src/vlttoo/memorytools/__init__.py
cp $WORKROOT/memorytools/requirements.txt $WORKROOT/pyvlttoo/src/vlttoo/memorytools
# cp -r $WORKROOT/memorytools/CCSTests/* 
cp memorymonitor.py memoryanalysis.py $WORKROOT/pyvlttoo/src/vlttoo/memorytools