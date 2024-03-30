import type { IconType } from "react-icons"
import { FaGithub, FaLinkedin, FaTwitter } from "react-icons/fa"
import { SiLeetcode } from "react-icons/si"
function Socials() {
  //make an array socials that has opjects with two properties one is src one is icon that is of IconType
  interface social { src: string, icon: IconType }
  const socials: social[] = [{ src: "www.github.com/abd-ulbasit", icon: FaGithub }, { src: "www.linkedin.com/in/abd-ulbasit", icon: FaLinkedin }, { src: "www.twitter.com/abd_lbasit", icon: FaTwitter }, { src: "www.leetcode.com/abd-ulbasit", icon: SiLeetcode }]
  return <div
    className="btn-group"
  >{socials.map((social) => {

    return <button key={social.src} onClick={(e) => { e.preventDefault(); window.open(`https://${social.src}`, "_blank") }}
      className="btn px-6 "
    >
      {<social.icon></social.icon>}
    </button>
  })
    }
  </div>

}
export default Socials;