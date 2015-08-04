while [ $# -gt 0 ] ; do
	nodeArg=$1
	
	IFS='/' read -a array <<< "$nodeArg"
	
	#nodeArg is just nodeXX
	id=${nodeArg:4:10}
	id=$(($id - 1))
	rackId=$(($id / 20))

	echo "/rack-${rackId}/"	

	shift
done
