/* 
	PHLib programming library for PicoHarp 300
	PicoQuant GmbH, December 2013
*/


#define LIB_VERSION "3.0" 

#define MAXDEVNUM	8

#define HISTCHAN	65536	// number of histogram channels
#define TTREADMAX   131072  // 128K event records

#define MODE_HIST	0
#define MODE_T2		2
#define MODE_T3		3

#define FEATURE_DLL       0x0001
#define FEATURE_TTTR      0x0002
#define FEATURE_MARKERS   0x0004 
#define FEATURE_LOWRES    0x0008 
#define FEATURE_TRIGOUT   0x0010

#define FLAG_FIFOFULL     0x0003  //T-modes
#define FLAG_OVERFLOW     0x0040  //Histomode
#define FLAG_SYSERROR     0x0100  //Hardware problem

#define BINSTEPSMAX 8

#define SYNCDIVMIN 1
#define SYNCDIVMAX 8

#define ZCMIN		0			//mV
#define ZCMAX		20			//mV
#define DISCRMIN	0			//mV
#define DISCRMAX	800			//mV

#define OFFSETMIN	0			//ps
#define OFFSETMAX	1000000000	//ps

#define SYNCOFFSMIN	-99999		//ps
#define SYNCOFFSMAX	 99999		//ps

#define CHANOFFSMIN -8000		//ps
#define CHANOFFSMAX  8000		//ps

#define ACQTMIN		1			//ms
#define ACQTMAX		360000000	//ms  (100*60*60*1000ms = 100h) 

#define PHR800LVMIN -1600		//mV
#define PHR800LVMAX  2400		//mV

#define HOLDOFFMAX  210480		//ns


//The following are bitmasks for return values from GetWarnings()

#define WARNING_INP0_RATE_ZERO				0x0001
#define WARNING_INP0_RATE_TOO_LOW			0x0002
#define WARNING_INP0_RATE_TOO_HIGH			0x0004

#define WARNING_INP1_RATE_ZERO				0x0010
#define WARNING_INP1_RATE_TOO_HIGH			0x0040

#define WARNING_INP_RATE_RATIO				0x0100
#define WARNING_DIVIDER_GREATER_ONE			0x0200
#define WARNING_TIME_SPAN_TOO_SMALL			0x0400
#define WARNING_OFFSET_UNNECESSARY			0x0800

