package main

import (
	"context"
	"fmt"

	"github.com/chromedp/chromedp"
)

func main2() {
	ctx, cancel := chromedp.NewContext(context.Background())
	defer cancel()

	var title string
	err := chromedp.Run(ctx,
		chromedp.Navigate("https://messages.google.com/web/welcome"),
		chromedp.Title(&title),
	)
	if err != nil {
		panic(err)
	}

	fmt.Println("Título da página:", title)
}
