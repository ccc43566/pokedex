const fs=require('node:fs/promises')
const path=require('node:path')
const root=path.resolve(__dirname,'../../UI/image/背景适配')
const web=path.resolve(__dirname,'../apps/web')
const sharp=require(path.join(web,'node_modules/.pnpm/sharp@0.35.5_@types+node@24.19.1/node_modules/sharp'))
async function main(){
 const {assets}=JSON.parse(await fs.readFile(path.join(root,'网页背景适配清单-v2.json'),'utf8'))
 const out=path.join(web,'public/catalog-backgrounds')
 await fs.mkdir(path.join(out,'thumbs'),{recursive:true})
 await sharp(path.join(web,'public/home/night/observatory-night.png')).webp({quality:90}).toFile(path.join(out,'observatory-night.webp'))
 await sharp(path.join(web,'public/home/night/observatory-night.png')).resize({width:480}).webp({quality:80}).toFile(path.join(out,'thumbs/night-1.webp'))
 const english={starters:'Kanto starters',snorlax:'Sleeping Snorlax',pastel:'Pastel friends',letter:'A letter from friends',pokeball:'Poké Ball silhouettes',pixel:'Pixel Pikachu',groudon:'Groudon & Kyogre',red:'Red',green:'Green',blue:'Blue','red-pikachu':'Red & Pikachu'}
 const results=[]
 for(const a of assets.filter(a=>a.form==='desktop')){
  const key=a.id.replace(/-desktop$/,'')
  const mobile=assets.find(v=>v.id===key+'-mobile')
  await fs.copyFile(path.join(root,a.webp),path.join(out,key+'-desktop.webp'))
  await fs.copyFile(path.join(root,a.thumbnail),path.join(out,'thumbs',key+'.webp'))
  if(mobile)await fs.copyFile(path.join(root,mobile.webp),path.join(out,key+'-mobile.webp'))
  const sample=async asset=>{
   const {data}=await sharp(path.join(root,asset.webp)).extract({left:Math.round(asset.width*.35),top:0,width:Math.round(asset.width*.3),height:Math.min(30,asset.height)}).resize(1,1).removeAlpha().raw().toBuffer({resolveWithObject:true})
   return '#'+[...data].slice(0,3).map(v=>v.toString(16).padStart(2,'0')).join('')
  }
  const description=['red','green','blue'].includes(key)?'纸色延展':a.mode==='day'?'日间插画':'夜间插画'
  results.push({id:a.mode+'-'+key,mode:a.mode,name:a.name,en:english[key],description,enDescription:description==='纸色延展'?'Paper illustration':a.mode==='day'?'Day illustration':'Night illustration',image:'/catalog-backgrounds/'+key+'-desktop.webp',mobileImage:mobile?'/catalog-backgrounds/'+key+'-mobile.webp':undefined,thumbnail:'/catalog-backgrounds/thumbs/'+key+'.webp',base:await sample(a),mobileBase:mobile?await sample(mobile):undefined,aspectRatio:a.width/a.height,mobileAspectRatio:mobile?mobile.width/mobile.height:undefined,size:'contain',position:'center bottom',overlay:a.mode==='day'?.12:key==='red-pikachu'?.32:.12,preview:`url('/catalog-backgrounds/thumbs/${key}.webp') center/cover`})
 }
 await fs.writeFile(path.join(web,'utils/catalogBackgrounds.ts'),'// Imported only from completed files. Regenerate with scripts/import-catalog-backgrounds.cjs.\nimport type { AppearanceBackground } from \'./appearance\'\nexport const catalogBackgrounds: AppearanceBackground[] = '+JSON.stringify(results,null,2)+'\n')
 console.log('Imported '+results.length+' selectable backgrounds; '+assets.filter(a=>a.form==='mobile').length+' mobile variants.')
}
main().catch(error=>{console.error(error);process.exitCode=1})
