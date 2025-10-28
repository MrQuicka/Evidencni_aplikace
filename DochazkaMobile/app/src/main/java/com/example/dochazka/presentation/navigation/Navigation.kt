package com.example.dochazka.presentation.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.example.dochazka.presentation.login.LoginScreen
import com.example.dochazka.presentation.logging.LoggingScreen

@Composable
fun AppNavigation() {
    val navController = rememberNavController()

    NavHost(
        navController = navController,
        startDestination = "login"
    ) {
        composable("login") {
            LoginScreen(
                onLoginSuccess = {
                    navController.navigate("logging") {
                        popUpTo("login") { inclusive = true }
                    }
                }
            )
        }

        composable("logging") {
            LoggingScreen(
                onLogout = {
                    navController.navigate("login") {
                        popUpTo("logging") { inclusive = true }
                    }
                }
            )
        }
    }
}
