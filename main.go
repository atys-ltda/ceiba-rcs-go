// Package main ...
package main

import (
	"fmt"
	"log"
	"time"

	"github.com/go-rod/rod"
	"github.com/go-rod/rod/lib/proto"
)

var qr string

func main() {
	browser := rod.New().MustConnect() // Sin interfaz grafica modo headless
	page := browser.MustPage("https://messages.google.com/web/authentication")

	// Desactivar los Service Workers
	err := proto.NetworkSetBypassServiceWorker{Bypass: true}.Call(page)
	if err != nil {
		log.Fatalf("Error al desactivar los Service Workers: %v", err)
	}

	page.MustSetWindow(2000, 0, 1400, 900)
	page.MustWaitDOMStable()
	page.MustScreenshot("QR.png")
	qr = *page.MustElement(".qr-code-wrapper").MustElement("img").MustAttribute("src")
	fmt.Printf("QR Time:%v\n", time.Now().Format("15:04:05"))

	// Obtener booton toggle id = mat-mdc-slide-toggle-0-button
	bRemember := page.MustElement("#mat-mdc-slide-toggle-0-button")
	bRemember.MustClick()

	Qr(browser, page)

	time.Sleep(time.Hour)
}

func Qr(b *rod.Browser, p *rod.Page) {
	// Interceptar solicitudes y respuestas
	router := p.HijackRequests()
	//defer router.MustStop()

	// capturarLaRespuestaDeLaSolicitud
	router.MustAdd("*/RefreshPhoneRelay", func(ctx *rod.Hijack) {
		// Continuar con la solicitud
		fmt.Println("Interceptando solicitudes 3...")
		// fmt.Printf("Int...: %+v\n", ctx.Request.Headers())
		ctx.ContinueRequest(&proto.FetchContinueRequest{})

		qr = *p.MustElement(".qr-code-wrapper").MustElement("img").MustAttribute("src")

	})

	go router.Run()
}
