import Head from "next/head";

export default function App({ Component, pageProps }) {
  return (
    <>
      <Head>
        <title>Davis — AI Lead Engine</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <style>{`
          * { box-sizing: border-box; margin: 0; padding: 0; }
          body { background: #111; color: #fff; }
        `}</style>
      </Head>
      <Component {...pageProps} />
    </>
  );
}
