/*
Controllo pannello solare
ottobre 2013
Roberto Chirio
rev. 1.3

*/


// variables :

int boiler = A0;   //  NTC Boiler connected to A0
int pann = A1;  //  NTC Panel connected to A1
int tempB = 0;         // variable to store the boiler temperature
int tempP = 0;         // variable to store the panel temperature

int BBB = 0;         // variable to store the boiler temperature in degree Celsius
int PPP = 0;         // variable to store the panel temperature in degree Celsius


void setup()
{
   Serial.begin(9600); 
   
    pinMode(11, OUTPUT);   // sets the pin 11
    pinMode(13, OUTPUT);   // sets the pin 13
 
  digitalWrite(11, LOW);   // set the 11 off
  
  digitalWrite(13, LOW);   // set the 13 off
  
  }



void loop()
{
  BBB = analogRead(boiler);   // read the boiler temperature
  PPP = analogRead(pann);   // read the panel temperature
  tempB=22011/BBB;
  tempP=22011/PPP;
  
   Serial.println("Boiler"); 
   Serial.println(tempB, DEC);       // monitor temperature BOILER
   Serial.println("Pannello"); 
   Serial.println(tempP, DEC);       // monitor temperature PANEL
   Serial.println("-------------"); 
   
   delay(1000);              // wait for a second
 

  // check if the Boiler temperature is to high >= 70°.
  // if it is, the ledTemp is HIGH and pompa off
  if (tempB > 70) {     
    // turn LED HItemp on:
    digitalWrite(11, HIGH); 
    // turn pompa OFF:
    digitalWrite(13, LOW); 
    delay(10000);              // wait for 10 second 
{ goto fineloop;}
}
  
  
  
  // check if the panel temperature is <= 20°.
  // if it is, the pompa is LOW:
  if (tempP <= 20) {     
    // turn pompa off:
    digitalWrite(13, LOW); 
   { goto fineloop;}
   }         
   
  
  // check if the temp panel is > of temp boiler
  // if it is, the pompa is on:
  if (tempP > tempB) {     
    // turn pompa on:
    digitalWrite(13, HIGH); 
    // turn led OFF:
    digitalWrite(11, LOW);
    delay(10000);              // wait for 15 second  
  } 

// check if the temp panel is <= of temp boiler
  // if it is, the pompa is off:
  if (tempP <= tempB) {     
    // turn pompa OFF:
    digitalWrite(13, LOW); 
    // turn led OFF:
    digitalWrite(11, LOW);
    delay(10000);              // wait for 15 second   
  } 
  
  fineloop:;
  
   }


