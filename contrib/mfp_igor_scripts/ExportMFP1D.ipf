#pragma rtGlobals=1		// Use modern global access method.
#pragma IgorVersion = 4.0
#pragma version = 0.4

//
// ExportMFP1D.ipf - A procedure to export force curves from MFP1D to 'hooke'
//
// Copyright (c) 2009 Rolf Schmidt, Montreal
// rschmidt@alcor.concordia.ca
// 
// This procedure is released under the GNU General Public License version 2
//

// History
// 2009 07 24: v0.4
// the wave note is now correctly and fully exported in Igor 4
// 2009 06 29: v0.3
// split functionality into ExportMFP1DFolder and ExportMFP1DWaves
// ExportMFP1DFolder: export individual Igor binary waves file from a folder
// ExportMFP1DWaves: export all currently open waves to a folder
// 2009 06 26: v0.2.1
// added the IgorVersion pragma
// 2009 06 19: v0.2
// changed the filename finding algorithm to work with Igor 4 and up
// Igor 5 users can use the code marked 'the following only works in Igor 5 and up' instead
// the procedure now catches 'Cancel' on NewPath
// added version information
// 2009 05 29: v0.1
// changed the procedure so that it runs in Igor as well as in MFP (ie Igor with MFP plug-in)

// How to use ExportMFP1D()
// - save all current waves of interest (ExportMFP1D() kills all open waves before exporting files)
// - execute ExportMFP1D() from the command line
// - browse to a folder containing force curves (a 'force curve' consists of two files: one 'deflection' and one 'LVDT' file
// - ExportMFP1D() will now iterate through all the waves in the folder, extract the header information and create four columns:
//   1: approach (x) 2: approach (y) 3: retraction (x) 4; retraction (y)
// - the resulting files are saved in the same folder and the same base name as the original files (ie without 'deflection' and 'LVDT')
// CAUTION:  existing files will be overwritten!
// - these files can then be analyzed with 'hooke'

Function ExportMFP1DFolder()

	String sList
	Variable iCount

	// set the path (used for opening the waves and saving the output files later)
	NewPath /O /Q /M="Choose the folder that contains the waves" PathExport1D

	KillWaves /A /Z
	
	if(V_flag>=0)
		// get a list of all Igor binary waves in the folder
		sList=IndexedFile(PathExport1D,-1,".ibw")
		// load all waves
		for(iCount=0; iCount<ItemsInList(sList); iCount+=1)
			LoadWave /P=PathExport1D /Q StringFromList(iCount, sList)
		endfor
		ExportMFP1DWaves()
	endif
	// kill the export path
	KillPath /Z PathExport1D
End

Function ExportMFP1DWaves()

	String sFileName1
	String sFileName2
	String sLine
	String sList
	String sNote
	String sWaveCombined
	String sWaveDeflection
	String sWaveLVDT
	Variable iCount
	Variable iLine
	Variable iPoints
	Variable iRefNum
	Wave wApproachX
	Wave wApproachY
	Wave wRetractionX
	Wave wRetractionY

	// set the path (used for saving the output files later)
	NewPath /O /Q /M="Choose the folder to save the waves" PathExport1D
	
	// get a list of all LVDT waves (could be deflection as well, they always come in a pair)
	sList=WaveList("*LVDT*", ";", "")
	
	// iterate through all the LVDT waves
	for(iCount=0; iCount<ItemsInList(sList); iCount+=1)
		// create the wave names as string
// the following only works in Igor 5 and up
//			sWaveLVDT=ReplaceString(".ibw",StringFromList(iCount, sList), "")
//			sWaveDeflection=ReplaceString("LVDT",sWaveLVDT, "deflection")
//			sWaveCombined=ReplaceString("LVDT",sWaveLVDT, "_")
// END: the following only works in Igor 5 and up

// the following works in Igor 4 and up
		// treat the filename as a key-value list with '.' as a separator
		// use the first entry (ie 0) as the filename without extension
		sWaveLVDT=StringFromList(0, StringFromList(iCount, sList), ".")
		
		// treat the filename as a key-value list with 'LVDT' as a separator
		// use the first entry (ie 0) as the first part of the filename
		sFileName1=StringFromList(0, sWaveLVDT, "LVDT")
		// getting the second part of the filename is a bit trickier
		// first, we 'remove' the first part of the filename by treating it as a key
		// using 'LVDT' as a separator 
		sFileName2=StringByKey(sFileName1, sWaveLVDT, "LVDT")
		// unfortunately, StringByKey only removes the first character of the separator
		// to get the second part of the filename, we use VD as the key and 'T' as the separator
		sFileName2=StringByKey("VD", sFileName2, "T")
		// then we create the wave names as follows:
		sWaveDeflection=sFileName1+"deflection"+sFileName2
		
		sWaveCombined=sFileName1+"_"+sFileName2
		
// END: the following works in Igor 4 and up

		// create the waves we need
		Wave wLVDT=$sWaveLVDT
		Wave wDeflection=$sWaveDeflection
	
		// open the output text file, add extension
		Open /P=PathExport1D iRefNum as sWaveCombined+".txt"

		// create the header
		fprintf iRefNum, "Wave:"+sWaveCombined+"\r"
		fprintf iRefNum, "WaveLVDT:"+sWaveLVDT+"\r"
		fprintf iRefNum, "WaveDeflection:"+sWaveDeflection+"\r"

		// the number of points (use WaveStats to get them) are identical for LVDT and Deflection
		WaveStats /q wLVDT
		iPoints=V_npnts/2
		fprintf iRefNum, "Rows:"+num2str(iPoints)+"\r"

		// add the note to the file
		// the notes are identical for LVDT and Deflection
// the following only works in Igor 5 and up
//		fprintf iRefNum, note(wDeflection)
// END: the following only works in Igor 5 and up
		sNote=note(wLVDT)
		// in order to get the correct number of lines in the note, we have to specify the EOF as \r\n
		for(iLine=0; iLine<ItemsInList(sNote, "\r\n");iLine+=1)
			// print every line to the output file
			fprintf iRefNum, StringFromList(iLine, sNote, "\r\n")
			// add a CR/LF for every but the last line
			if(iLine<ItemsInList(sNote, "\r\n")-1)
				fprintf iRefNum, "\r\n"
			endif
		endfor

		// separate the approach from the retraction
		// by simply taking the first half of the points to be the approach
		// and the second half to be the retraction
		// this probably has to be changed for dual pulls
		Duplicate /O /R=[0, iPoints] wLVDT, wApproachX
		Duplicate /O /R=[0, iPoints] wDeflection, wApproachY
		Duplicate /O /R=[iPoints+1] wLVDT, wRetractionX
		Duplicate /O /R=[iPoints+1] wDeflection, wRetractionY

		// create four columns line by line
		// 1: approach x 2: approach y 3: retraction x 4: retraction y
		for(iLine=0; iLine<iPoints; iLine+=1)
			sLine=num2str(wApproachX[iLine])+"\t"+num2str(wApproachY[iLine])
			sLine=sLine+"\t"+num2str(wRetractionX[iLine])+"\t"+num2str(wRetractionY[iLine])
			// add the line to the file
			fprintf iRefNum, "\r"+sLine
		endfor

		// save the text file to disk
		print "Exporting "+sWaveCombined
		Close iRefNum
	endfor

	// print message
	print "Export completed ("+num2str(ItemsInList(sList))+" files)"

	// kill the temporary waves used
	// given the names, it is unlikely that this function will interfere with data
	KillWaves /Z wApproachX
	KillWaves /Z wApproachY
	KillWaves /Z wRetractionX
	KillWaves /Z wRetractionY
End
