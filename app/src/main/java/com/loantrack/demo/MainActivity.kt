package com.loantrack.demo

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.net.HttpURLConnection
import java.net.URL

private val Green = Color(0xFF005C3B)
private val Lime = Color(0xFFB6D438)

class MainActivity : ComponentActivity() {
 override fun onCreate(savedInstanceState: Bundle?) { super.onCreate(savedInstanceState); setContent { LoanTrackApp() } }
}

@Composable fun LoanTrackApp() {
 var url by remember { mutableStateOf("https://YOUR-LOANTRACK-URL.onrender.com") }
 var username by remember { mutableStateOf("") }; var password by remember { mutableStateOf("") }
 var result by remember { mutableStateOf("") }; var signedIn by remember { mutableStateOf(false) }
 val scope = rememberCoroutineScope()
 MaterialTheme(colorScheme = lightColorScheme(primary=Green, secondary=Lime)) {
  Surface(modifier=Modifier.fillMaxSize()) { Column(modifier=Modifier.fillMaxSize().padding(20.dp), verticalArrangement=Arrangement.spacedBy(14.dp)) {
   Text("LoanTrack", fontSize=29.sp, fontWeight=FontWeight.Bold, color=Green); Text("Native Android demonstration app", color=Color.Gray)
   if (!signedIn) {
    Text("Connect to your LoanTrack Render app", fontWeight=FontWeight.Bold); OutlinedTextField(url,{url=it},label={Text("Render URL")},singleLine=true,modifier=Modifier.fillMaxWidth())
    OutlinedTextField(username,{username=it},label={Text("Application ID or staff username")},singleLine=true,modifier=Modifier.fillMaxWidth())
    OutlinedTextField(password,{password=it},label={Text("Demo PIN or password")},singleLine=true,modifier=Modifier.fillMaxWidth())
    Button(onClick={ scope.launch { result="Signing in..."; result=login(url,username,password); signedIn=result.startsWith("Welcome") } },modifier=Modifier.fillMaxWidth(),colors=ButtonDefaults.buttonColors(containerColor=Green)){Text("Sign in")}
    Text("Demo accounts: LT-260912-041 / 2468 or manager.demo / Manager2026!",fontSize=12.sp,color=Color.Gray)
   } else {
    Card(colors=CardDefaults.cardColors(containerColor=Color(0xFFEAF4E8)),modifier=Modifier.fillMaxWidth()) { Column(Modifier.padding(18.dp)){Text(result,fontWeight=FontWeight.Bold); Spacer(Modifier.height(8.dp)); Text("The native app is connected to the LoanTrack demonstration backend. Use the officer web dashboard to update fictional applications, documents and collateral simulation results.")}}
    LinearProgressIndicator(progress={0.6f},modifier=Modifier.fillMaxWidth(),color=Green,trackColor=Color(0xFFDDE8E0)); Text("Loan progress demonstration: 60% complete",fontWeight=FontWeight.Medium)
    Button(onClick={signedIn=false;result=""},modifier=Modifier.fillMaxWidth(),colors=ButtonDefaults.buttonColors(containerColor=Green)){Text("Sign out")}
   }
   if(result.isNotBlank() && !signedIn) Text(result,color=if(result.startsWith("Error")) Color.Red else Color.Gray)
  }}
 }
}

suspend fun login(base:String, username:String, password:String):String = withContext(Dispatchers.IO) {
 try { val connection=(URL(base.trimEnd('/')+"/api/demo/login").openConnection() as HttpURLConnection).apply { requestMethod="POST"; doOutput=true; setRequestProperty("Content-Type","application/json"); outputStream.use{it.write("{\"username\":\"${username.replace("\"","\\\"")}\",\"password\":\"${password.replace("\"","\\\"")}\"}".toByteArray())} }; val body=connection.inputStream.bufferedReader().readText(); if(connection.responseCode in 200..299) "Welcome - demo connection confirmed" else "Error: demo sign-in failed" } catch(e:Exception) { "Error: could not connect. Check the Render URL and redeploy the updated backend." }
}
