def fcurves_all(action):
	print(action)
	BLENDER_VERSION = 5
	fcurves = None
	if BLENDER_VERSION == 5:
		print("layers: ", action.layers)
		for layer in action.layers:
			strips = layer.strips
			print("strips: ", strips)
			for strip in strips:
				print("bags: ", strip.channelbags)
				for bag in strip.channelbags:
					fcurves = bag.fcurves
					print("fcurves: ", fcurves)
					break;
				break;
			break;
	else:
		fcurves = action.fcurves
	return fcurves