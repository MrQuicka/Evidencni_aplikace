package com.example.dochazka

import android.app.Application
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class DocházkaApplication : Application() {
    override fun onCreate() {
        super.onCreate()
    }
}
